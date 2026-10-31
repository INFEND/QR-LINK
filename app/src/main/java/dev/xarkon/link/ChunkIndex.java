package dev.xarkon.link;

/** Reject malformed or out-of-range chunk URLs before touching received data. */
final class ChunkIndex {
    private ChunkIndex(){}
    static int parse(String value,int count){
        if(value==null||value.isEmpty()||value.length()>10||count<=0)return -1;
        long number=0;
        for(int i=0;i<value.length();i++){
            char ch=value.charAt(i);
            if(ch<'0'||ch>'9')return -1;
            number=number*10+(ch-'0');
            if(number>=count)return -1;
        }
        return (int)number;
    }
}
