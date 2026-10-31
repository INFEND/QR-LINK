package dev.xarkon.link;

/** Direction and filename are independent of the localized progress verb. */
public final class TransferLabel {
    private TransferLabel(){}
    public static String direction(String label){
        if(label==null)return "";
        if(label.startsWith("Приём: ")||label.startsWith("Получено: "))return "Приём";
        if(label.startsWith("Отправка: ")||label.startsWith("Готово: "))return "Отправка";
        return "";
    }
    public static String file(String label){
        if(label==null)return "";
        int sep=label.indexOf(": ");
        return sep<0?label:label.substring(sep+2);
    }
}
