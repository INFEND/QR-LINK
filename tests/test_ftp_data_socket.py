"""JVM regression: FTP passive sockets close on connection/setup errors; progress uses SIZE."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/dev/xarkon/link"
HARNESS = r'''package dev.xarkon.link;
import java.io.IOException;
import java.net.*;
public final class FtpDataSocketCheck {
    static class FakeSocket extends Socket {
        boolean failConnect, failTimeout, closed;
        int timeout;
        @Override public void connect(SocketAddress address,int connectTimeout) throws IOException {
            if(connectTimeout!=5000) throw new AssertionError("Wrong connect timeout");
            if(failConnect) throw new ConnectException("Simulated connection failure");
        }
        @Override public synchronized void setSoTimeout(int value) throws SocketException {
            timeout=value;
            if(failTimeout) throw new SocketException("Simulated timeout setup failure");
        }
        @Override public synchronized void close() throws IOException {closed=true;}
    }
    static void check(boolean condition){if(!condition)throw new AssertionError();}
    public static void main(String[] args)throws Exception {
        SocketAddress address=new InetSocketAddress("127.0.0.1",2121);
        FakeSocket ok=new FakeSocket();
        check(FtpDataSocket.connect(ok,address)==ok);
        check(!ok.closed&&ok.timeout==30000);
        FakeSocket refused=new FakeSocket();refused.failConnect=true;
        try{FtpDataSocket.connect(refused,address);throw new AssertionError("No connect failure");}
        catch(ConnectException expected){}
        check(refused.closed);
        FakeSocket badTimeout=new FakeSocket();badTimeout.failTimeout=true;
        try{FtpDataSocket.connect(badTimeout,address);throw new AssertionError("No timeout failure");}
        catch(SocketException expected){}
        check(badTimeout.closed);
    }
}
'''

class FtpDataSocketTests(unittest.TestCase):
    def test_passive_socket_lifecycle_jvm(self):
        with tempfile.TemporaryDirectory() as work:
            harness = Path(work) / "FtpDataSocketCheck.java"
            harness.write_text(HARNESS, encoding="utf-8")
            subprocess.run(["javac", "-encoding", "UTF-8", "-d", work,
                str(JAVA / "FtpDataSocket.java"), str(harness)],
                check=True, capture_output=True, text=True)
            subprocess.run(["java", "-cp", work, "dev.xarkon.link.FtpDataSocketCheck"],
                check=True, capture_output=True, text=True)

    def test_ftp_progress_uses_real_advertised_total(self):
        source = (JAVA / "FtpBridge.java").read_text(encoding="utf-8")
        self.assertIn("return FtpDataSocket.connect(host,dataport);", source)
        self.assertIn('events.progress("ShareMe FTP: "+name,total,expectedBytes,', source)
        self.assertNotIn('events.progress("ShareMe FTP: "+name,total,-1,', source)
        self.assertLess(source.index("FtpSizeReply.expectedBytes(sizeCode,last)"),
            source.index('events.progress("ShareMe FTP: "+name,total,expectedBytes,'))

if __name__ == "__main__":
    unittest.main()
