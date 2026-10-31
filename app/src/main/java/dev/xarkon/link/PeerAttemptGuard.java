package dev.xarkon.link;
import java.util.concurrent.atomic.AtomicInteger;
/** Invalidates late P2P, hotspot and /hello callbacks after reconnect/disconnect. */
final class PeerAttemptGuard {
    private final AtomicInteger generation=new AtomicInteger();
    int next(){return generation.incrementAndGet();}
    boolean current(int token){return generation.get()==token;}
    int snapshot(){return generation.get();}
    /** A failed /pair must not invalidate an established peer. */
    int advanceIfCurrent(int token){return generation.compareAndSet(token,token+1)?token+1:-1;}
}
