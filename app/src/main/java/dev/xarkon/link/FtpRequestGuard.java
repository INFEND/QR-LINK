package dev.xarkon.link;

/** Invalidates stale asynchronous FTP directory results and failures. */
final class FtpRequestGuard {
    private long generation;
    synchronized long begin() { return ++generation; }
    synchronized void invalidate() { ++generation; }
    synchronized boolean isCurrent(long token) { return token == generation; }
}
