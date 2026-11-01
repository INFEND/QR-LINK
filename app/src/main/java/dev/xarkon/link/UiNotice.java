package dev.xarkon.link;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.widget.LinearLayout;
import android.widget.PopupWindow;
import android.widget.TextView;

/** Lightweight in-app notices, independent of the system Toast theme. */
public final class UiNotice {
    public static final int INFO=0,ERROR=1,SUCCESS=2;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private PopupWindow popup;
    private Runnable timeout;

    public void show(Activity activity,String message,int accent,int card,int text,int kind){
        if(activity==null||activity.isFinishing()||activity.isDestroyed())return;
        View anchor=activity.getWindow().getDecorView();
        if(!anchor.isAttachedToWindow()){
            anchor.post(()->show(activity,message,accent,card,text,kind));
            return;
        }
        dismiss();
        float density=activity.getResources().getDisplayMetrics().density;
        int dp=(int)(density+0.5f);
        int border=kind==ERROR?0xffb94c58:accent;
        LinearLayout row=new LinearLayout(activity);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(14*dp,11*dp,14*dp,11*dp);
        GradientDrawable background=new GradientDrawable();
        background.setColor(card);
        background.setCornerRadius(14*dp);
        background.setStroke(dp,border);
        row.setBackground(background);
        UiIcon icon=new UiIcon(activity,kind==ERROR?"close":kind==SUCCESS?"check":"info",border);
        row.addView(icon,new LinearLayout.LayoutParams(28*dp,28*dp));
        TextView label=new TextView(activity);
        label.setText(message);label.setTextSize(13);label.setTextColor(text);
        label.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,-2,1);
        params.leftMargin=10*dp;row.addView(label,params);
        PopupWindow notice=new PopupWindow(row,
            Math.min(activity.getResources().getDisplayMetrics().widthPixels-28*dp,450*dp),-2);
        notice.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        notice.setFocusable(false);notice.setTouchable(false);notice.setElevation(10*dp);
        WindowInsets insets=anchor.getRootWindowInsets();
        int top=insets==null?24*dp:Build.VERSION.SDK_INT>=30?
            insets.getInsets(WindowInsets.Type.statusBars()).top:insets.getSystemWindowInsetTop();
        notice.showAtLocation(anchor,Gravity.TOP|Gravity.CENTER_HORIZONTAL,0,top+10*dp);
        popup=notice;
        row.setAlpha(0f);row.setTranslationY(-10*dp);
        row.animate().alpha(1f).translationY(0f).setDuration(170).start();
        timeout=()->{
            if(popup!=notice)return;
            row.animate().alpha(0f).translationY(-10*dp).setDuration(170)
                .withEndAction(()->{if(popup==notice){notice.dismiss();popup=null;}}).start();
        };
        handler.postDelayed(timeout,kind==ERROR?4400:2700);
    }
    public void dismiss(){
        if(timeout!=null){handler.removeCallbacks(timeout);timeout=null;}
        if(popup!=null){popup.dismiss();popup=null;}
    }
}
