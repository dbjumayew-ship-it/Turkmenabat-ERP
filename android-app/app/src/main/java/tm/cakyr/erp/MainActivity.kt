package tm.cakyr.erp
import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.*
import androidx.appcompat.app.AppCompatActivity
class MainActivity:AppCompatActivity(){ lateinit var w:WebView
@SuppressLint("SetJavaScriptEnabled") override fun onCreate(b:Bundle?){super.onCreate(b);w=WebView(this);setContentView(w);w.settings.javaScriptEnabled=true;w.settings.domStorageEnabled=true;w.webViewClient=WebViewClient();w.webChromeClient=WebChromeClient();w.loadUrl(getString(R.string.server_url))}
override fun onBackPressed(){if(w.canGoBack())w.goBack() else super.onBackPressed()} }
