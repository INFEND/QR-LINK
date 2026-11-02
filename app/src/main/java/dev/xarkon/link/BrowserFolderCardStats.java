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
    interface ProgressListener {
        void onProgress(int fileCount,long countedBytes);
    }
    static BrowserFolderCardStats scanLocal(java.nio.file.Path folder,
                                             java.nio.file.Path sharedRoot)
            throws java.io.IOException {
        return scanLocal(folder,sharedRoot,null);
    }
    static BrowserFolderCardStats scanLocal(java.nio.file.Path folder,
                                             java.nio.file.Path sharedRoot,
                                             ProgressListener progress)
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
                    if(progress!=null&&count[0]%512==0)
                        progress.onProgress(count[0],total[0]);
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

    /** Stream SAF document metadata without building a transfer queue. A
     * provider may repeat document IDs; count identical files only once and
     * reject cycles, inconsistent metadata or inaccessible descendants.
     * The reader owns and closes each provider cursor before returning.
     */
    interface DocumentChildVisitor {
        void accept(String documentId,boolean directory,long bytes) throws java.io.IOException;
    }
    interface DocumentChildReader {
        void readChildren(String parentId,DocumentChildVisitor visitor) throws java.io.IOException;
    }
    static BrowserFolderCardStats scanDocuments(String rootId,DocumentChildReader reader)
            throws java.io.IOException {
        return scanDocuments(rootId,reader,null);
    }
    static BrowserFolderCardStats scanDocuments(String rootId,DocumentChildReader reader,
                                                 ProgressListener progress)
            throws java.io.IOException {
        if(rootId==null||rootId.trim().isEmpty()||reader==null)
            throw new java.io.IOException("Недоступная папка");
        java.util.ArrayDeque<String> pending=new java.util.ArrayDeque<>();
        java.util.HashSet<String> seenDirs=new java.util.HashSet<>();
        java.util.HashMap<String,Long> seenFiles=new java.util.HashMap<>();
        final int[] count={0};
        final long[] total={0};
        final boolean[] known={true};
        pending.add(rootId);
        seenDirs.add(rootId);
        while(!pending.isEmpty()){
            if(Thread.currentThread().isInterrupted())
                throw new java.io.IOException("Подсчёт отменён");
            String parent=pending.removeFirst();
            reader.readChildren(parent,(id,directory,size)->{
                if(Thread.currentThread().isInterrupted())
                    throw new java.io.IOException("Подсчёт отменён");
                if(id==null||id.trim().isEmpty())
                    throw new java.io.IOException("Элемент без идентификатора");
                if(directory){
                    if(seenFiles.containsKey(id)||!seenDirs.add(id))
                        throw new java.io.IOException("Повторяющийся или циклический каталог");
                    pending.addLast(id);
                    return;
                }
                // A SAF document ID cannot be both a file and a directory.
                if(seenDirs.contains(id))
                    throw new java.io.IOException("Несогласованный тип документа");
                Long previous=seenFiles.putIfAbsent(id,size);
                if(previous!=null){
                    if(previous.longValue()!=size)
                        throw new java.io.IOException("Несогласованный размер документа");
                    return;
                }
                if(count[0]==Integer.MAX_VALUE)
                    throw new java.io.IOException("Слишком много файлов");
                count[0]++;
                if(size<0||Long.MAX_VALUE-total[0]<size)known[0]=false;
                else total[0]+=size;
                if(progress!=null&&count[0]%512==0)
                    progress.onProgress(count[0],total[0]);
            });
        }
        return new BrowserFolderCardStats(count[0],total[0],true,known[0]);
    }
}
