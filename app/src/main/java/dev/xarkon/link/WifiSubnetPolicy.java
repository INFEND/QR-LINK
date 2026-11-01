package dev.xarkon.link;

/** DNS-free IPv4 subnet check. Only used for guidance, never for blocking
 * a potentially routed, working connection between different subnets.
 */
final class WifiSubnetPolicy {
    private WifiSubnetPolicy(){}
    private static long parse(String ip){
        if(ip==null)return -1L;
        String[] parts=ip.split("\\.",-1);
        if(parts.length!=4)return -1L;
        long value=0;
        for(String part:parts){
            if(part.isEmpty()||part.length()>3)return -1L;
            int n=0;
            for(int j=0;j<part.length();j++){
                char c=part.charAt(j);
                if(c<'0'||c>'9')return -1L;
                n=n*10+c-'0';
            }
            if(n>255)return -1L;
            value=(value<<8)|n;
        }
        return value;
    }
    static boolean sameSubnet(String local,String peer,int prefix){
        if(prefix<0||prefix>32)return false;
        long a=parse(local),b=parse(peer);
        if(a<0||b<0)return false;
        long mask=prefix==0?0L:(0xffffffffL<<(32-prefix))&0xffffffffL;
        return (a&mask)==(b&mask);
    }
}
