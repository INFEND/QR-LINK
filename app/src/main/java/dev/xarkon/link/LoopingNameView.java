package dev.xarkon.link;

import android.animation.ValueAnimator;
import android.content.Context;
import android.text.Layout;
import android.view.animation.LinearInterpolator;
import android.widget.TextView;

/** Smoothly scrolls clipped names, pauses at both ends, and never jumps between cycles. */
public final class LoopingNameView extends TextView {
    private ValueAnimator motion;
    private int previousWidth=-1;
    public LoopingNameView(Context context){
        super(context);
        setSingleLine(true);
        setEllipsize(null);
        setHorizontallyScrolling(true);
    }
    @Override protected void onAttachedToWindow(){
        super.onAttachedToWindow();
        post(this::restartIfNeeded);
    }
    @Override protected void onSizeChanged(int w,int h,int oldw,int oldh){
        super.onSizeChanged(w,h,oldw,oldh);
        if(w!=oldw)post(this::restartIfNeeded);
    }
    @Override protected void onTextChanged(CharSequence text,int start,int before,int count){
        super.onTextChanged(text,start,before,count);
        if(getWidth()>0)post(this::restartIfNeeded);
    }
    private void restartIfNeeded(){
        if(!isAttachedToWindow()||getWidth()<=0)return;
        Layout layout=getLayout();
        if(layout==null||layout.getLineCount()==0)return;
        int overflow=Math.max(0,(int)Math.ceil(layout.getLineWidth(0))-getWidth()+getPaddingLeft()+getPaddingRight());
        if(overflow==previousWidth&&motion!=null&&motion.isRunning())return;
        previousWidth=overflow;
        if(motion!=null){motion.cancel();motion=null;}
        setScrollX(0);
        if(overflow<=0)return;
        // Keyframes: pause at the start, scroll left, pause at the end, return smoothly.
        motion=ValueAnimator.ofFloat(0f,0f,1f,1f,0f);
        motion.setInterpolator(new LinearInterpolator());
        motion.setDuration(Math.max(4800L,overflow*28L+2800L));
        motion.setRepeatCount(ValueAnimator.INFINITE);
        motion.addUpdateListener(animation->setScrollX(Math.round(
            overflow*(Float)animation.getAnimatedValue())));
        motion.start();
    }
    @Override protected void onDetachedFromWindow(){
        if(motion!=null){motion.cancel();motion=null;}
        previousWidth=-1;setScrollX(0);
        super.onDetachedFromWindow();
    }
}
