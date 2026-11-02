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
        Set<String> names=new HashSet<>();
        StringBuilder result=new StringBuilder();
        long lastSelected=installed;
        for(Entry entry:history) {
            if(entry==null)return latestNotes;
            // The historical archive predates the installed app. Malformed or
            // obsolete entries from BEFORE that version must never suppress
            // valid changelog entries for the versions the user actually missed.
            if(entry.code<=installed)continue;
            if(entry.code<=lastSelected||entry.code>latest||
                entry.name==null||entry.name.isEmpty()||!names.add(entry.name)||
                entry.notes==null||entry.notes.length()>100_000) return latestNotes;
            // A missing intermediate release must not be silently presented as
            // a complete changelog. History is indexed by published versionCode.
            if(entry.code>lastSelected+1)return latestNotes;
            String clean=ReleaseNotes.visible(entry.notes);
            if(clean.isEmpty())return latestNotes;
            lastSelected=entry.code;
            if(result.length()>0)result.append('\n');
            result.append(clean);
        }
        if(lastSelected!=latest)return latestNotes;
        return result.toString();
    }
}
