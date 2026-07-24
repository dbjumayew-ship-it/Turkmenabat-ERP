package tm.turkmenabat.erp

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.view.View
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import tm.turkmenabat.erp.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val serverUrl: String by lazy { getString(R.string.server_url) }
    private val serverHost: String by lazy { Uri.parse(serverUrl).host.orEmpty() }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(binding.webView, true)
        }

        binding.webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            builtInZoomControls = false
            displayZoomControls = false
            loadWithOverviewMode = true
            useWideViewPort = true
            userAgentString = "$userAgentString TurkmenabatERP-Android/0.9"
        }

        binding.webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                binding.progressBar.progress = newProgress
                binding.progressBar.visibility =
                    if (newProgress >= 100) View.GONE else View.VISIBLE
                binding.swipeRefresh.isRefreshing = false
            }
        }

        binding.webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest
            ): Boolean {
                val uri = request.url
                return if (uri.host == serverHost) {
                    false
                } else {
                    startActivity(Intent(Intent.ACTION_VIEW, uri))
                    true
                }
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                binding.offlinePanel.visibility = View.GONE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                binding.swipeRefresh.isRefreshing = false
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: android.webkit.WebResourceError?
            ) {
                if (request?.isForMainFrame == true) showOffline()
            }
        }

        binding.webView.setDownloadListener(
            DownloadListener { url, _, _, _, _ ->
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        )

        binding.swipeRefresh.setOnRefreshListener {
            if (isOnline()) binding.webView.reload() else showOffline()
        }

        binding.retryButton.setOnClickListener {
            loadErp()
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                when {
                    binding.offlinePanel.visibility == View.VISIBLE -> loadErp()
                    binding.webView.canGoBack() -> binding.webView.goBack()
                    else -> finish()
                }
            }
        })

        if (savedInstanceState == null) {
            loadErp()
        } else {
            binding.webView.restoreState(savedInstanceState)
        }
    }

    private fun loadErp() {
        if (!isOnline()) {
            showOffline()
            return
        }
        binding.offlinePanel.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
        binding.webView.loadUrl(serverUrl)
    }

    private fun showOffline() {
        binding.swipeRefresh.isRefreshing = false
        binding.progressBar.visibility = View.GONE
        binding.webView.visibility = View.GONE
        binding.offlinePanel.visibility = View.VISIBLE
    }

    private fun isOnline(): Boolean {
        val manager = getSystemService(ConnectivityManager::class.java)
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    @Suppress("unused")
    private fun printCurrentPage() {
        val printManager = getSystemService(PRINT_SERVICE) as PrintManager
        val adapter = binding.webView.createPrintDocumentAdapter("Turkmenabat ERP")
        printManager.print(
            "Turkmenabat ERP",
            adapter,
            PrintAttributes.Builder().build()
        )
    }

    override fun onSaveInstanceState(outState: Bundle) {
        binding.webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }
}
