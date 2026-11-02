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
        return scanLocal(folder,sharedRoot,progress,29);
    }
    /** Android 11+ may return an empty filtered listing for protected descendants. */
    static BrowserFolderCardStats scanLocal(java.nio.file.Path folder,
                                             java.nio.file.Path sharedRoot,
                                             ProgressListener progress,int androidSdk)
            throws java.io.IOException {
        java.nio.file.Path base=sharedRoot.toRealPath();
        if(java.nio.file.Files.isSymbolicLink(folder))
            throw new java.io.IOException("Символическая ссылка вместо папки");
        java.nio.file.Path selected=folder.toRealPath();
        if(!selected.startsWith(base)||!java.nio.file.Files.isDirectory(selected))
            throw new java.io.IOException("Папка вне внутренней памяти");
        final int[] count={0};
        final long[] total={0};
        // Track direct children per directory, not a list of every file.
        final java.util.ArrayDeque<Integer> observedChildren=new java.util.ArrayDeque<>();
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
                    if(!observedChildren.isEmpty()){
                        int count=observedChildren.pop();
                        observedChildren.push(count+1);
                    }
                    observedChildren.push(0);
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
                    int siblings=observedChildren.pop();
                    observedChildren.push(siblings+1);
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
                    int children=observedChildren.pop();
                    BrowserFolderAccess.requireVisibleEvidence(
                        base.relativize(dir).toString(),androidSdk,children);
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
    /** Optional metadata fallback, evaluated after provider cursors have closed. */
    interface DocumentSizeResolver {
        long resolve(String documentId) throws java.io.IOException;
    }
    static BrowserFolderCardStats scanDocuments(String rootId,DocumentChildReader reader)
            throws java.io.IOException {
        return scanDocuments(rootId,reader,null);
    }
    static BrowserFolderCardStats scanDocuments(String rootId,DocumentChildReader reader,
                                                 ProgressListener progress)
            throws java.io.IOException {
        return scanDocuments(rootId,reader,null,progress);
    }
    static BrowserFolderCardStats scanDocuments(String rootId,DocumentChildReader reader,
                                                 DocumentSizeResolver resolver,
                                                 ProgressListener progress)
            throws java.io.IOException {
        if(rootId==null||rootId.trim().isEmpty()||reader==null)
            throw new java.io.IOException("Недоступная папка");
        java.util.ArrayDeque<String> pending=new java.util.ArrayDeque<>();
        java.util.HashSet<String> seenDirs=new java.util.HashSet<>();
        // Some SAF providers repeat a child row in the same parent cursor.
        // A second parent or a back-edge is an alias/cycle and must fail closed.
        java.util.HashMap<String,String> directoryParents=new java.util.HashMap<>();
        java.util.HashMap<String,Long> seenFiles=new java.util.HashMap<>();
        final int[] count={0};
        final long[] total={0};
        final boolean[] known={true};
        final boolean[] missing={false};
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
                    if(seenFiles.containsKey(id))
                        throw new java.io.IOException("Несогласованный тип документа");
                    if(seenDirs.contains(id)){
                        // A duplicate row from the *same* parent is harmless;
                        // never traverse it twice or count its children twice.
                        if(parent.equals(directoryParents.get(id)))return;
                        throw new java.io.IOException("Повторяющийся или циклический каталог");
                    }
                    seenDirs.add(id);
                    directoryParents.put(id,parent);
                    pending.addLast(id);
                    return;
                }
                // A SAF document ID cannot be both a file and a directory.
                if(seenDirs.contains(id))
                    throw new java.io.IOException("Несогласованный тип документа");
                Long previous=seenFiles.get(id);
                if(previous!=null){
                    // A provider may repeat the same document, first without
                    // COLUMN_SIZE and later with an exact size (or vice versa).
                    // Only conflicting *known* sizes are inconsistent.
                    if(previous>=0&&size>=0&&previous.longValue()!=size)
                        throw new java.io.IOException("Несогласованный размер документа");
                    if(previous<0&&size>=0){
                        seenFiles.put(id,size);
                        if(Long.MAX_VALUE-total[0]<size)known[0]=false;
                        else total[0]+=size;
                    }
                    return;
                }
                seenFiles.put(id,size);
                if(count[0]==Integer.MAX_VALUE)
                    throw new java.io.IOException("Слишком много файлов");
                count[0]++;
                if(size<0){missing[0]=true;known[0]=false;}
                else if(Long.MAX_VALUE-total[0]<size)known[0]=false;
                else total[0]+=size;
                if(progress!=null&&count[0]%512==0)
                    progress.onProgress(count[0],total[0]);
            });
        }
        // Some SAF providers omit COLUMN_SIZE but expose a regular descriptor.
        // Resolve only missing sizes, after closing every query cursor. Never
        // read file contents or mistake a pipe/unknown descriptor for zero.
        if(missing[0]){
            // Recompute after all duplicate rows have been reconciled. A
            // later exact COLUMN_SIZE may resolve an earlier unknown size
            // without opening a descriptor at all.
            long exact=0;
            boolean exactKnown=true;
            for(Map.Entry<String,Long> entry:seenFiles.entrySet()){
                if(Thread.currentThread().isInterrupted())
                    throw new java.io.IOException("Подсчёт отменён");
                long size=entry.getValue();
                if(size<0&&resolver!=null)size=resolver.resolve(entry.getKey());
                if(size<0||Long.MAX_VALUE-exact<size)exactKnown=false;
                else exact+=size;
            }
            return new BrowserFolderCardStats(count[0],exact,true,exactKnown);
        }
        return new BrowserFolderCardStats(count[0],total[0],true,known[0]);
    }
}
