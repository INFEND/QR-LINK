package dev.xarkon.link;

import java.util.regex.Pattern;

/** Strict metadata validation before creating any MediaStore destination. */
public final class TransferFileIdentity {
    private static final Pattern UUID=Pattern.compile(
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
    private static final Pattern MIME=Pattern.compile(
        "[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+");
    private static final Pattern SHA=Pattern.compile("[0-9a-fA-F]{64}");
    private TransferFileIdentity(){}
    public static boolean validId(String id){
        return id!=null&&UUID.matcher(id).matches();
    }
    public static boolean validMime(String mime){
        return mime!=null&&mime.length()<=127&&MIME.matcher(mime).matches();
    }
    /** Normalize unusual SAF MIME types without accepting unsafe metadata over HTTP. */
    public static String safeMime(String mime){
        return validMime(mime)?mime:"application/octet-stream";
    }
    public static boolean validSha256(String sha){
        return sha!=null&&SHA.matcher(sha).matches();
    }
}
