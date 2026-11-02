package dev.xarkon.link;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Human-readable Russian messages for the most common Android/network errors. */
public final class ErrorText {
    private ErrorText(){}
    private static final Pattern HTTP=Pattern.compile("(?i)\\bHTTP\\s*(\\d{3})\\b");
    private static String remoteMessage(String raw){
        int field=raw.indexOf("\"error\"");
        if(field<0)return "";
        int colon=raw.indexOf(':',field+7);
        if(colon<0)return "";
        int begin=raw.indexOf('"',colon+1);
        if(begin<0)return "";
        int end=raw.indexOf('"',begin+1);
        if(end<=begin||end-begin>241)return "";
        String value=raw.substring(begin+1,end);
        // Remote error bodies are untrusted. Never render controls, bidi
        // overrides, escaped JSON or internal exception traces in a UI banner.
        if(value.length()>160||value.indexOf('\\')>=0)return "";
        for(int i=0;i<value.length();i++){
            char ch=value.charAt(i);
            if(Character.isISOControl(ch)||ch=='\\u202a'||ch=='\\u202b'||
               ch=='\\u202d'||ch=='\\u202e'||ch=='\\u2066'||
               ch=='\\u2067'||ch=='\\u2068'||ch=='\\u2069')return "";
        }
        String lower=value.toLowerCase(Locale.ROOT);
        if(lower.contains("exception")||lower.contains("stacktrace")||
           lower.contains("java.")||lower.contains("android.")||
           lower.contains("libcore."))return "";
        return value.matches(".*[А-Яа-яЁё].*")?value:"";
    }
    /** Preserve the actionable root cause when a wrapper contains only an OEM error. */
    public static String human(Throwable error){
        if(error==null)return human((String)null);
        String fallback=human(error.getMessage());
        if(!generic(fallback))return fallback;
        java.util.IdentityHashMap<Throwable,Boolean> visited=new java.util.IdentityHashMap<>();
        Throwable cause=error;
        for(int depth=0;cause!=null&&depth<8&&visited.put(cause,Boolean.TRUE)==null;depth++){
            if(cause!=error){
                String localized=human(cause.getMessage());
                if(!generic(localized))return localized;
            }
            cause=cause.getCause();
        }
        return fallback;
    }
    private static boolean generic(String text){
        return text.startsWith("Не удалось выполнить операцию.");
    }
    public static String human(String message){
        if(message==null||message.trim().isEmpty())
            return "Не удалось выполнить операцию. Повторите попытку.";
        String lower=message.toLowerCase(Locale.ROOT);
        if(lower.contains("sslhandshake")||lower.contains("certificate_unknown")||
           lower.contains("certpathvalidatorexception")||lower.contains("trust anchor"))
            return "Ошибка проверки защищённого соединения. Проверьте дату, время и настройки VPN.";
        if(lower.contains("unknownhost")||lower.contains("unable to resolve host")||
           lower.contains("no address associated with hostname")||
           lower.contains("name or service not known"))
            return "Не удалось определить адрес устройства или сервера. Проверьте подключение и DNS.";
        if(lower.contains("connection refused")||lower.contains("econnrefused"))
            return "Получатель отклонил соединение. Откройте QR LINK на принимающем устройстве.";
        if(lower.contains("no route to host")||lower.contains("network is unreachable")||
           lower.contains("enetunreach")||lower.contains("ehostunreach"))
            return "Нет маршрута до получателя. Проверьте Wi-Fi и соединение между устройствами.";
        if(lower.contains("sockettimeout")||lower.contains("timed out")||
           lower.contains("timeout")||lower.contains("etimedout"))
            return "Превышено время ожидания. Убедитесь, что получатель находится рядом и готов к передаче.";
        if(lower.contains("broken pipe")||lower.contains("connection reset")||
           lower.contains("econnreset"))
            return "Соединение прервалось. Непереданные файлы можно отправить повторно.";
        if(lower.contains("permission denied")||lower.contains("securityexception")||
           lower.contains("eacces"))
            return "Не хватает разрешений Android. Проверьте доступ к файлам и устройствам поблизости.";
        if(lower.contains("cleartext communication")||lower.contains("not permitted by network security policy"))
            return "Незащищённое сетевое соединение заблокировано Android.";
        if(lower.contains("no space left")||lower.contains("enospc"))
            return "Недостаточно свободного места на устройстве.";
        if(lower.contains("file not found")||lower.contains("enoent"))
            return "Исходный файл недоступен или был перемещён.";
        if(lower.contains("unable to open")||lower.contains("failed to open"))
            return "Не удалось открыть файл. Проверьте доступ и повторите попытку.";
        Matcher http=HTTP.matcher(message);
        if(http.find()){
            String remote=remoteMessage(message);
            if(!remote.isEmpty())return remote;
            String code=http.group(1);
            if("401".equals(code)||"403".equals(code))
                return "Сервер отклонил доступ. Проверьте разрешения и авторизацию.";
            if("404".equals(code))
                return "Запрошенный файл или адрес не найден на сервере.";
            if("429".equals(code))
                return "Слишком много запросов. Повторите попытку позже.";
            if(code.charAt(0)=='5')
                return "Сервер временно недоступен. Повторите попытку позже.";
            return "Сервер ответил ошибкой "+code+". Повторите попытку.";
        }
        // Preserve existing informative Russian messages, but never expose
        // unlocalized low-level exception dumps to end users.
        if(message.matches(".*[А-Яа-яЁё].*")){
            if(lower.contains("java.")||lower.contains("exception:")||
               lower.contains("android.")||lower.contains("libcore."))
                return "Не удалось выполнить операцию. Проверьте соединение и разрешения Android.";
            return message;
        }
        return "Не удалось выполнить операцию. Проверьте подключение и повторите попытку.";
    }
}
