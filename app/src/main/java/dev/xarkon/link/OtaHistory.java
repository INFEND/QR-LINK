package dev.xarkon.link;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** VersionCode-based cumulative OTA notes. Pure Java so it can be regression-tested offline. */
public final class OtaHistory {
    private OtaHistory() {}

    public static final class Entry {
        public final long code;
        public final String name;
        public final String notes;
        public Entry(long code, String name, String notes) {
            this.code=code;
            this.name=name;
            this.notes=notes;
        }
    }

    /**
     * Show every published version after the installed version.
     * Reject malformed/incomplete metadata instead of displaying a misleading partial history.
     * Legacy manifests (no history) retain their last-release notes.
     */
    public static String merge(List<Entry> history,long installed,long latest,String fallback) {
        String latestNotes=ReleaseNotes.visible(fallback);
        if(history==null||history.isEmpty()||installed>=latest)return latestNotes;
        long previous=0;
        Set<String> names=new HashSet<>();
        StringBuilder result=new StringBuilder();
        boolean selected=false;
        long lastSelected=installed;
        for(Entry entry:history) {
            if(entry==null||entry.code<=previous||entry.code>latest||
                entry.name==null||entry.name.isEmpty()||!names.add(entry.name)||
                entry.notes==null||entry.notes.length()>100_000) return latestNotes;
            previous=entry.code;
            String clean=ReleaseNotes.visible(entry.notes);
            if(clean.isEmpty())return latestNotes;
            if(entry.code>installed) {
                if(entry.code>lastSelected+1)return latestNotes;
                lastSelected=entry.code;
                if(result.length()>0)result.append('\n');
                result.append(clean);
                selected=true;
            }
        }
        if(previous!=latest||!selected)return latestNotes;
        return result.toString();
    }
}
