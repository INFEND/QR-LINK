package dev.xarkon.link;

import java.util.concurrent.atomic.AtomicLong;

/** In-process invalidation for the persistent transfer queue. */
final class QueueRevision {
    private static final AtomicLong revision=new AtomicLong();
    private QueueRevision(){}
    static long current(){return revision.get();}
    static void changed(){revision.incrementAndGet();}
}
