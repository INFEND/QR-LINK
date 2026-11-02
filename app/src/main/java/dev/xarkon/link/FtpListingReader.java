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
}
