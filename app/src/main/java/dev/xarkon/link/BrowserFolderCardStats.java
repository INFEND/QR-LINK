package dev.xarkon.link;

import java.util.Map;

/** Constant-size summary for a folder card; no file URIs are retained. */
final class BrowserFolderCardStats {
    final int fileCount;
    final long bytes;
    final boolean complete,bytesKnown;

    private BrowserFolderCardStats(int fileCount,long bytes,boolean complete,boolean bytesKnown){
        this.fileCount=fileCount;
        this.bytes=bytes;
        this.complete=complete;
        this.bytesKnown=bytesKnown;
    }

    static BrowserFolderCardStats summarize(Map<String,Long> files,boolean complete){
        long total=0;
        boolean known=complete;
        for(Long value:files.values()){
            if(value==null||value<0||Long.MAX_VALUE-total<value){
                known=false;
            }else total+=value;
        }
        return new BrowserFolderCardStats(files.size(),total,complete,known);
    }

    /**
     * Stream exact shared-storage folder totals without materializing a
     * 30000-entry transfer queue. No links are followed; unreadable entries,
     * overflow and cancellation fail closed rather than publishing a partial size.
     */
    static BrowserFolderCardStats scanLocal(java.nio.file.Path folder,
                                             java.nio.file.Path sharedRoot)
            throws java.io.IOException {
        java.nio.file.Path base=sharedRoot.toRealPath();
        if(java.nio.file.Files.isSymbolicLink(folder))
            throw new java.io.IOException("Символическая ссылка вместо папки");
        java.nio.file.Path selected=folder.toRealPath();
        if(!selected.startsWith(base)||!java.nio.file.Files.isDirectory(selected))
            throw new java.io.IOException("Папка вне внутренней памяти");
        final int[] count={0};
        final long[] total={0};
        java.nio.file.Files.walkFileTree(selected,
            java.util.EnumSet.noneOf(java.nio.file.FileVisitOption.class),
            Integer.MAX_VALUE,new java.nio.file.SimpleFileVisitor<java.nio.file.Path>(){
                private void checkActive()throws java.io.IOException{
                    if(Thread.currentThread().isInterrupted())
                        throw new java.io.IOException("Подсчёт отменён");
                }
                @Override public java.nio.file.FileVisitResult preVisitDirectory(
                        java.nio.file.Path dir,java.nio.file.attribute.BasicFileAttributes attrs)
                        throws java.io.IOException{
                    checkActive();
                    if(attrs.isSymbolicLink()||!java.nio.file.Files.isReadable(dir))
                        throw new java.io.IOException("Недоступная папка");
                    return java.nio.file.FileVisitResult.CONTINUE;
                }
                @Override public java.nio.file.FileVisitResult visitFile(
                        java.nio.file.Path file,java.nio.file.attribute.BasicFileAttributes attrs)
                        throws java.io.IOException{
                    checkActive();
                    if(!attrs.isRegularFile()||!java.nio.file.Files.isReadable(file))
                        throw new java.io.IOException("Недоступный элемент папки");
                    long size=attrs.size();
                    if(count[0]==Integer.MAX_VALUE||size<0||Long.MAX_VALUE-total[0]<size)
                        throw new java.io.IOException("Размер папки слишком велик");
                    count[0]++;
                    total[0]+=size;
                    return java.nio.file.FileVisitResult.CONTINUE;
                }
                @Override public java.nio.file.FileVisitResult visitFileFailed(
                        java.nio.file.Path file,java.io.IOException error)
                        throws java.io.IOException{
                    throw error;
                }
                @Override public java.nio.file.FileVisitResult postVisitDirectory(
                        java.nio.file.Path dir,java.io.IOException error)
                        throws java.io.IOException{
                    if(error!=null)throw error;
                    return java.nio.file.FileVisitResult.CONTINUE;
                }
            });
        return new BrowserFolderCardStats(count[0],total[0],true,true);
    }
}
