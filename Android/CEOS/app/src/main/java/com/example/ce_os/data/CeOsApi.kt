package os.ce.node.data

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class CeOsStatus(
    val node: String = "pixel",
    val requestedMode: String = "unknown",
    val effectiveMode: String = "unknown",
    val platformState: String = "unknown",
    val requestedUsbMode: String = "none",
    val usbMode: String = "none",
    val allowCompute: Boolean = false,
    val powerState: String = "unknown",
    val thermalState: String = "unknown",
    val battery: String = "unknown",
    val batteryTempC: String = "unknown",
    val thermalStatus: String = "unknown",
    val timestamp: String = "",
    val reasons: List<String> = emptyList()
)

data class BootstrapStatus(
    val active: Boolean,
    val effectiveMode: String,
    val g1Udc: String,
    val g2Udc: String,
    val hal: String,
    val state: String
)

data class BootstrapResult(
    val ok: Boolean,
    val active: Boolean,
    val leaseSeconds: Int = 0,
    val error: String? = null
)

data class PlatformVerification(
    val ok: Boolean,
    val platformState: String,
    val error: String? = null
)

object CeOsApi {
    private const val BASE = "http://127.0.0.1:8765"
    private const val TOKEN_FILE = "ceos_token"

    private var appContext: Context? = null

    fun configure(context: Context) {
        appContext = context.applicationContext
    }

    private fun token(): String? {
        val context = appContext ?: return null
        val file = context.filesDir.resolve(TOKEN_FILE)

        if (!file.isFile) {
            return null
        }

        return file.readText().trim().takeIf { it.isNotEmpty() }
    }

    private fun connection(
        path: String,
        method: String,
        privileged: Boolean = false
    ): HttpURLConnection {
        return (URL("$BASE$path").openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 3000
            readTimeout = 15000
            useCaches = false

            if (privileged) {
                val credential = token()
                    ?: error("CE-OS privileged control is not paired")

                setRequestProperty(
                    "X-CEOS-Token",
                    credential
                )
            }
        }
    }

    private fun request(
        path: String,
        method: String = "GET",
        privileged: Boolean = false
    ): JSONObject {
        val conn = connection(path, method, privileged)

        try {
            val code = conn.responseCode

            val stream =
                if (code in 200..299) conn.inputStream
                else conn.errorStream

            val body = stream
                ?.bufferedReader()
                ?.use { it.readText() }
                .orEmpty()

            if (code !in 200..299) {
                error("CE-OS API HTTP $code: $body")
            }

            return JSONObject(body)
        } finally {
            conn.disconnect()
        }
    }

    fun status(): CeOsStatus {
        val json = request("/v1/status")

        val reasonsJson = json.optJSONArray("guardian_reasons")
        val reasons = mutableListOf<String>()

        if (reasonsJson != null) {
            for (i in 0 until reasonsJson.length()) {
                reasons += reasonsJson.optString(i)
            }
        }

        val telemetry = json.optJSONObject("telemetry")

        return CeOsStatus(
            node = json.optString("node", "pixel"),
            requestedMode = json.optString("requested_mode", "unknown"),
            effectiveMode = json.optString("effective_mode", "unknown"),
            platformState = json.optString("platform_state", "unknown"),
            requestedUsbMode = json.optString("requested_usb_mode", "none"),
            usbMode = json.optString("usb_mode", "none"),
            allowCompute = json.optInt("allow_compute", 0) == 1,
            powerState = json.optString("power_state", "unknown"),
            thermalState = json.optString("thermal_state", "unknown"),
            battery = telemetry?.optString("battery", "unknown") ?: "unknown",
            batteryTempC = telemetry?.optString("battery_temp_c", "unknown") ?: "unknown",
            thermalStatus = telemetry?.optString("thermal_status", "unknown") ?: "unknown",
            timestamp = telemetry?.optString("timestamp", "") ?: "",
            reasons = reasons,
        )
    }

    fun setMode(mode: String): CeOsStatus {
        require(
            mode == "node" ||
                mode == "conserve" ||
                mode == "bootstrap"
        )

        request(
            "/v1/mode/$mode",
            "POST"
        )

        return status()
    }

    fun bootstrapStatus(): BootstrapStatus {
        val json = request(
            "/v1/privileged/bootstrap/status",
            privileged = true
        )

        val effectiveMode =
            json.optString("effective_mode", "android")

        val state =
            json.optString("state", "unknown")

        return BootstrapStatus(
            active =
                effectiveMode == "bootstrap" &&
                    state == "ceos",
            effectiveMode = effectiveMode,
            g1Udc = json.optString("g1_udc", ""),
            g2Udc = json.optString("g2_udc", ""),
            hal = json.optString("hal", "unknown"),
            state = state
        )
    }

    fun enableBootstrap(): BootstrapResult {
        Log.i("CEOS-Control", "bootstrap enable requested")

        // Record operator intent before requesting privileged
        // hardware realization.
        setMode("bootstrap")

        Log.i("CEOS-Control", "bootstrap intent accepted")

        val json = request(
            "/v1/privileged/bootstrap/enable",
            method = "POST",
            privileged = true
        )

        Log.i("CEOS-Control", "bootstrap privileged enable returned")

        return BootstrapResult(
            ok = json.optBoolean("ok", false),
            active =
                json.optString("effective_mode") == "bootstrap" &&
                    json.optString("state") == "ceos",
            leaseSeconds = json.optInt("lease_seconds", 0),
            error = json.optString("error")
                .takeIf { it.isNotBlank() }
        )
    }

    fun disableBootstrap(): BootstrapResult {
        val json = request(
            "/v1/privileged/bootstrap/disable",
            method = "POST",
            privileged = true
        )

        return BootstrapResult(
            ok = json.optBoolean("ok", false),
            active = false,
            error = json.optString("error")
                .takeIf { it.isNotBlank() }
        )
    }

    fun verifyPlatform(): PlatformVerification {
        val json = request(
            "/v1/privileged/platform/verify",
            privileged = true
        )

        val platform = json.optJSONObject("platform")

        return PlatformVerification(
            ok = json.optBoolean("ok", false),
            platformState = platform?.optString(
                "platform_state",
                "unknown"
            ) ?: "unknown",
            error = json.optString("error")
                .takeIf { it.isNotBlank() }
        )
    }
}
