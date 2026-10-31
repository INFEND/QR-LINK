package dev.xarkon.link;

import java.util.Locale;
import java.util.Set;

/** Category-only visibility filter. Folder selection always collects all files. */
final class BrowserCategoryFilter {
    private static final Set<String> IMAGES=Set.of("jpg","jpeg","png","gif","webp","bmp","heic","heif","avif","tif","tiff","dng","raw","svg");
    private static final Set<String> VIDEOS=Set.of("mp4","mkv","avi","mov","webm","3gp","m4v","ts","mpeg","mpg","flv");
    private static final Set<String> AUDIO=Set.of("mp3","m4a","aac","flac","wav","ogg","opus","wma","aiff","alac","amr");
    private static final Set<String> PACKAGES=Set.of("apk","apks","xapk");

    private BrowserCategoryFilter() {}

    static boolean accepts(int category,String filename,String mime){
        if(category<0||category==4)return true;
        String name=filename==null?"":filename.toLowerCase(Locale.ROOT);
        int dot=name.lastIndexOf('.');
        String extension=dot<0?"":name.substring(dot+1);
        String type=mime==null?"":mime.toLowerCase(Locale.ROOT);
        switch(category){
            case 0:return type.startsWith("image/")||IMAGES.contains(extension);
            case 1:return type.startsWith("video/")||VIDEOS.contains(extension);
            case 2:return type.startsWith("audio/")||AUDIO.contains(extension);
            case 3:return PACKAGES.contains(extension);
            default:return false;
        }
    }
}
