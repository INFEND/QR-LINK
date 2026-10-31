package dev.xarkon.link;

/** Segment-aware ancestry: DCIM/A is not an ancestor of DCIM/AB. */
public final class BrowserPathRules {
    private BrowserPathRules(){}
    public static boolean isSameOrDescendant(String child,String parent){
        if(child==null||parent==null)return false;
        if(parent.isEmpty())return true;
        return child.equals(parent)||child.startsWith(parent+"/");
    }
}
