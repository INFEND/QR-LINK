"""Regression: nested Android exceptions and untrusted HTTP errors stay readable."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link/ErrorText.java"

HARNESS = r'''package dev.xarkon.link;
import java.io.IOException;
public final class ErrorCauseCheck {
    private static void expect(boolean ok, String name) {
        if (!ok) throw new AssertionError(name);
    }
    public static void main(String[] args) {
        Exception wrapped = new Exception("OEM HAL 0x4a",
            new IOException("connection refused"));
        expect(ErrorText.human(wrapped).contains("Получатель отклонил"),
            "nested connection error");
        Exception nestedPermission = new Exception("OEM error",
            new IOException("permission denied"));
        expect(ErrorText.human(nestedPermission).contains("разрешений"),
            "nested permission error");
        expect("Папка недоступна".equals(ErrorText.human(
            new IOException("Папка недоступна", new IOException("connection refused")))),
            "Russian parent message must be preserved");
        expect(ErrorText.human((Throwable)null).contains("Повторите"),
            "null throwable");
        Throwable first = new Throwable("OEM driver");
        Throwable second = new Throwable("OEM error");
        first.initCause(second);
        second.initCause(first);
        expect(ErrorText.human(first).startsWith("Не удалось"),
            "cyclic cause must terminate");

        // Some Android providers and network stacks supply no error text.
        // The exception class must still yield a useful Russian message.
        expect(ErrorText.human(new SecurityException()).contains("разрешений"),
            "empty SecurityException");
        expect(ErrorText.human(new java.nio.file.AccessDeniedException("/sdcard/file"))
            .contains("разрешений"), "AccessDeniedException");
        expect(ErrorText.human(new java.net.UnknownHostException()).contains("DNS"),
            "empty UnknownHostException");
        expect(ErrorText.human(new java.net.SocketTimeoutException()).contains("ожидания"),
            "empty SocketTimeoutException");
        expect(ErrorText.human(new java.net.ConnectException()).contains("подключиться"),
            "empty ConnectException");
        expect(ErrorText.human(new java.io.FileNotFoundException()).contains("файл"),
            "empty FileNotFoundException");
        expect(ErrorText.human(new Exception("OEM 0x91",
            new java.net.SocketTimeoutException())).contains("ожидания"),
            "nested exception with no message");

        String safe = ErrorText.human("HTTP 409 {\"error\":\"Передача уже завершена\"}");
        expect(safe.equals("Передача уже завершена"), "safe Russian server error");
        String newline = ErrorText.human("HTTP 500 {\"error\":\"Ошибка\nподменённый заголовок\"}");
        expect(!newline.contains("\n") && !newline.contains("подменённый"),
            "reject remote control characters");
        String bidi = ErrorText.human("HTTP 500 {\"error\":\"Ошибка\u202eскрытый текст\"}");
        expect(!bidi.contains("скрытый"), "reject bidi controls");
        String trace = ErrorText.human("HTTP 500 {\"error\":\"Ошибка java.lang.Exception\"}");
        expect(!trace.contains("java."), "reject server exception traces");
        expect(ErrorText.human("HTTP 401").contains("доступ"), "401");
        expect(ErrorText.human("HTTP 404").contains("не найден"), "404");
        expect(ErrorText.human("HTTP 429").contains("много запросов"), "429");
        expect(ErrorText.human("HTTP 503").contains("временно недоступен"), "503");
    }
}
'''

class ErrorCauseAndServerMessageTests(unittest.TestCase):
    def test_localized_nested_errors_and_http_responses(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "ErrorCauseCheck.java"
            source.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", work,
                            str(JAVA), str(source)],
                           check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", work, "dev.xarkon.link.ErrorCauseCheck"],
                           check=True, capture_output=True, text=True)

if __name__ == "__main__":
    unittest.main()
