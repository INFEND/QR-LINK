package dev.xarkon.link;

import java.io.IOException;
import java.io.Reader;

/** Bounds untrusted FTP directory listings without relying on unbounded readLine(). */
final class FtpListingReader {
    static final int MAX_LINE_CHARS = 4096;
    static final int MAX_ENTRIES = 100_000;

    private FtpListingReader() {}

    static String readLine(Reader input) throws IOException {
        StringBuilder line = new StringBuilder();
        while (true) {
            int value = input.read();
            if (value < 0) return line.length() == 0 ? null : line.toString();
            if (value == '\n') {
                if (line.length() > 0 && line.charAt(line.length() - 1) == '\r')
                    line.setLength(line.length() - 1);
                return line.toString();
            }
            if (value == 0 || (Character.isISOControl((char) value) && value != '\r' && value != '\t'))
                throw new IOException("Некорректная строка списка FTP");
            if (line.length() >= MAX_LINE_CHARS)
                throw new IOException("Слишком длинное имя в списке FTP");
            line.append((char) value);
        }
    }

    static void requireCapacity(int existingEntries) throws IOException {
        if (existingEntries >= MAX_ENTRIES)
            throw new IOException("Слишком много файлов в папке FTP");
    }

    static boolean safeName(String name) {
        if (name == null || name.isEmpty() || name.equals(".") || name.equals("..")) return false;
        for (int i = 0; i < name.length(); i++) {
            char ch = name.charAt(i);
            if (ch == '/' || ch == '\\' || Character.isISOControl(ch) ||
                (ch >= '\u202a' && ch <= '\u202e') || (ch >= '\u2066' && ch <= '\u2069'))
                return false;
        }
        return true;
    }

    /** Only ordinary files and folders from Unix LIST are downloadable. */
    static boolean supportedUnixType(String permissions) {
        if (permissions == null || permissions.length() < 10) return false;
        char type = permissions.charAt(0);
        if (type != '-' && type != 'd') return false;
        for (int i = 1; i <= 9; i++) {
            char flag = permissions.charAt(i);
            if (flag != 'r' && flag != 'w' && flag != 'x' && flag != '-' &&
                flag != 's' && flag != 'S' && flag != 't' && flag != 'T')
                return false;
        }
        return true;
    }

    /** Windows/DOS FTP LIST: date, time, <DIR>/size and file name. */
    private static final java.util.regex.Pattern DOS_LIST = java.util.regex.Pattern.compile(
        "^\\d{2}-\\d{2}-\\d{2,4}\\s+\\d{1,2}:\\d{2}(?:AM|PM)\\s+(<DIR>|\\d+)\\s+(.+)$",
        java.util.regex.Pattern.CASE_INSENSITIVE);
    private static final java.util.regex.Pattern DOS_PREFIX = java.util.regex.Pattern.compile(
        "^\\d{2}-\\d{2}-\\d{2,4}\\s+.*");

    static final class ListedEntry {
        final String name;
        final boolean directory;
        final long size;
        ListedEntry(String name, boolean directory, long size) {
            this.name = name; this.directory = directory; this.size = size;
        }
    }

    static ListedEntry parseDosEntry(String line) {
        if (line == null) return null;
        java.util.regex.Matcher match = DOS_LIST.matcher(line.trim());
        if (!match.matches()) return null;
        String name = match.group(2);
        if (!safeName(name)) return null;
        boolean directory = match.group(1).equalsIgnoreCase("<DIR>");
        try {
            return new ListedEntry(name, directory,
                directory ? -1 : Long.parseLong(match.group(1)));
        } catch (NumberFormatException ignored) { return null; }
    }

    /** Malformed DOS records must not appear as fabricated file names. */
    static boolean looksLikeDosLine(String line) {
        return line != null && DOS_PREFIX.matcher(line.trim()).matches();
    }
}
