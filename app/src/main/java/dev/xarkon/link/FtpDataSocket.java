package dev.xarkon.link;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketAddress;

/** Close a passive FTP data socket if either connection or timeout setup fails. */
final class FtpDataSocket {
    private FtpDataSocket() {}

    static Socket connect(String host,int port) throws IOException {
        return connect(new Socket(),new InetSocketAddress(host,port));
    }

    static Socket connect(Socket socket,SocketAddress address) throws IOException {
        try {
            socket.connect(address,5000);
            socket.setSoTimeout(30000);
            return socket;
        } catch(IOException|RuntimeException failure) {
            try {socket.close();} catch(IOException ignored) {}
            throw failure;
        }
    }
}
