package dev.xarkon.link;

import java.io.BufferedReader;
import java.io.EOFException;
import java.io.IOException;

/** Bounded, strict reader for FTP control replies from an untrusted device. */
final class FtpReplyReader {
    private static final int MAX_LINE = 4096;
    private static final int MAX_REPLY_LINES = 64;

    static final class Reply {
        final int code;
        final String lastLine;
        Reply(int code, String lastLine) { this.code = code; this.lastLine = lastLine; }
    }

    private FtpReplyReader() {}

    static Reply read(BufferedReader input) throws IOException {
        String first = readLine(input);
        int code = status(first);
        if (first.charAt(3) == ' ') return new Reply(code, first);
        String marker = first.substring(0, 3) + " ";
        for (int count = 1; count < MAX_REPLY_LINES; count++) {
            String next = readLine(input);
            if (next.startsWith(marker)) return new Reply(code, next);
        }
        throw new IOException("Слишком длинный ответ FTP-сервера");
    }

    private static int status(String line) throws IOException {
        if (line.length() < 4 || (line.charAt(3) != ' ' && line.charAt(3) != '-') ||
            line.charAt(0) < '1' || line.charAt(0) > '5' ||
            line.charAt(1) < '0' || line.charAt(1) > '9' ||
            line.charAt(2) < '0' || line.charAt(2) > '9') {
            throw new IOException("Некорректный ответ FTP-сервера");
        }
        return (line.charAt(0) - '0') * 100 + (line.charAt(1) - '0') * 10 + line.charAt(2) - '0';
    }

    private static String readLine(BufferedReader input) throws IOException {
        StringBuilder line = new StringBuilder();
        for (int i = 0; i <= MAX_LINE; i++) {
            int value = input.read();
            if (value < 0) throw new EOFException("FTP-сервер закрыл соединение");
            if (value == '\n') {
                if (line.length() > 0 && line.charAt(line.length() - 1) == '\r')
                    line.setLength(line.length() - 1);
                return line.toString();
            }
            if (value == 0 || (value < 32 && value != '\r' && value != '\t'))
                throw new IOException("Некорректный ответ FTP-сервера");
            if (line.length() >= MAX_LINE) throw new IOException("Слишком длинный ответ FTP-сервера");
            line.append((char) value);
        }
        throw new IOException("Слишком длинный ответ FTP-сервера");
    }
}
