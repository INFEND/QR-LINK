package dev.xarkon.link;

import android.app.Activity;
import android.app.Dialog;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Reusable accent-aware confirmation sheet with animated entry and exit. */
public final class UiConfirmDialog {
    private UiConfirmDialog(){}
    private static int dp(Activity a,float n){return (int)(a.getResources().getDisplayMetrics().density*n+.5f);}
    private static GradientDrawable shape(Activity a,int fill,int border,int radius){
        GradientDrawable d=new GradientDrawable();d.setColor(fill);d.setCornerRadius(dp(a,radius));
        if(border!=0)d.setStroke(dp(a,1),border);return d;
    }
    private static TextView label(Activity a,String text,int size,int color,boolean bold){
        TextView v=new TextView(a);v.setText(text);v.setTextSize(size);v.setTextColor(color);
        v.setIncludeFontPadding(false);if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        return v;
    }
    private static void close(Activity a,Dialog dialog,View card,boolean animate,Runnable action){
        if(!dialog.isShowing())return;
        Runnable finish=()->{dialog.dismiss();if(action!=null&&!a.isFinishing()&&!a.isDestroyed())action.run();};
        card.animate().cancel();
        if(animate)card.animate().alpha(0f).scaleX(.97f).scaleY(.97f)
            .setDuration(155).withEndAction(finish).start();
        else finish.run();
    }
    public static Dialog show(Activity a,String title,String message,String positiveLabel,Runnable action){
        return showInternal(a,title,message,positiveLabel,action,false);
    }
    /** Single-action AMOLED explanation with a restriction icon and close button. */
    public static Dialog showInfo(Activity a,String title,String message){
        return showInternal(a,title,message,"ПОНЯТНО",null,true);
    }
    private static Dialog showInternal(Activity a,String title,String message,
                                       String positiveLabel,Runnable action,boolean infoOnly){
        if(a==null||a.isFinishing()||a.isDestroyed())return null;
        SharedPreferences prefs=a.getSharedPreferences("settings",0);
        String mode=prefs.getString("theme_mode","dark");
        boolean light="light".equals(mode),amoled="amoled".equals(mode);
        boolean animate=prefs.getBoolean("motion",true);
        int accent=prefs.getInt("accent",0xff55dfcb);
        int foreground=light?0xff182837:0xfff5f7f9;
        int muted=light?0xff617689:0xffa0adb8;
        int panel=light?0xffffffff:amoled?0xff101013:0xff14212d;
        int stroke=light?0xffdce4ed:amoled?0xff303036:0xff304252;
        int accentText=Color.red(accent)*299+Color.green(accent)*587+
            Color.blue(accent)*114>160000?0xff07161b:Color.WHITE;
        Dialog dialog=new Dialog(a);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        LinearLayout card=new LinearLayout(a);card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(a,21),dp(a,20),dp(a,21),dp(a,19));
        card.setBackground(shape(a,panel,stroke,23));
        LinearLayout heading=new LinearLayout(a);heading.setGravity(Gravity.CENTER_VERTICAL);
        heading.addView(infoOnly?new UiIcon(a,"close",accent):new UiIcon(a,"info",accent),
            new LinearLayout.LayoutParams(dp(a,29),dp(a,29)));
        TextView titleView=label(a,title,19,foreground,true);
        LinearLayout.LayoutParams titleLp=new LinearLayout.LayoutParams(0,-2,1);
        titleLp.leftMargin=dp(a,12);heading.addView(titleView,titleLp);card.addView(heading);
        ScrollView scroll=new ScrollView(a);scroll.setVerticalScrollBarEnabled(false);
        TextView details=label(a,message,14,muted,false);details.setLineSpacing(dp(a,3),1f);
        scroll.addView(details);
        LinearLayout.LayoutParams bodyLp=new LinearLayout.LayoutParams(-1,-2);
        bodyLp.topMargin=dp(a,16);card.addView(scroll,bodyLp);
        LinearLayout buttons=new LinearLayout(a);buttons.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams buttonsLp=new LinearLayout.LayoutParams(-1,-2);
        buttonsLp.topMargin=dp(a,22);card.addView(buttons,buttonsLp);
        LinearLayout cancel=new LinearLayout(a);cancel.setGravity(Gravity.CENTER);
        cancel.setPadding(dp(a,8),dp(a,13),dp(a,8),dp(a,13));
        cancel.setBackground(new RippleDrawable(ColorStateList.valueOf(accent&0x33ffffff),
            shape(a,light?0xfff1f5f8:0xff202a31,stroke,13),null));
        cancel.addView(new UiIcon(a,"close",accent),new LinearLayout.LayoutParams(dp(a,18),dp(a,18)));
        TextView cancelText=label(a,"ОТМЕНА",12,foreground,true);
        LinearLayout.LayoutParams cancelTextLp=new LinearLayout.LayoutParams(-2,-2);
        cancelTextLp.leftMargin=dp(a,6);cancel.addView(cancelText,cancelTextLp);
        if(!infoOnly)buttons.addView(cancel,new LinearLayout.LayoutParams(0,-2,1));
        LinearLayout accept=new LinearLayout(a);accept.setGravity(Gravity.CENTER);
        accept.setPadding(dp(a,8),dp(a,13),dp(a,8),dp(a,13));
        accept.setBackground(new RippleDrawable(ColorStateList.valueOf(0x44000000),
            shape(a,accent,0,13),null));
        accept.addView(new UiIcon(a,"check",accentText),new LinearLayout.LayoutParams(dp(a,18),dp(a,18)));
        TextView acceptText=label(a,positiveLabel,12,accentText,true);
        LinearLayout.LayoutParams acceptTextLp=new LinearLayout.LayoutParams(-2,-2);
        acceptTextLp.leftMargin=dp(a,6);accept.addView(acceptText,acceptTextLp);
        LinearLayout.LayoutParams acceptLp=new LinearLayout.LayoutParams(0,-2,1.25f);
        if(!infoOnly)acceptLp.leftMargin=dp(a,9);
        buttons.addView(accept,acceptLp);
        cancel.setContentDescription("Отмена");accept.setContentDescription(positiveLabel);
        cancel.setOnClickListener(v->close(a,dialog,card,animate,null));
        accept.setOnClickListener(v->close(a,dialog,card,animate,action));
        dialog.setContentView(card);dialog.setCanceledOnTouchOutside(true);
        Window window=dialog.getWindow();
        if(window!=null){
            window.setBackgroundDrawableResource(android.R.color.transparent);
            window.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);
            WindowManager.LayoutParams params=window.getAttributes();params.dimAmount=.64f;
            window.setAttributes(params);
        }
        dialog.show();
        if(window!=null)window.setLayout(Math.min(a.getResources().getDisplayMetrics().widthPixels-dp(a,32),
            dp(a,440)),WindowManager.LayoutParams.WRAP_CONTENT);
        if(animate){
            card.setAlpha(0f);card.setScaleX(.96f);card.setScaleY(.96f);
            card.animate().alpha(1f).scaleX(1f).scaleY(1f).setDuration(195).start();
        }
        return dialog;
    }
}
