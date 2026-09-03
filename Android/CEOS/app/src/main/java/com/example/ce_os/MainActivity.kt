package os.ce.node

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import os.ce.node.theme.CEOSTheme
import os.ce.node.data.CeOsApi
import os.ce.node.bridge.GodotLaunchBridge
import os.ce.node.ui.main.MainScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        CeOsApi.configure(this)
        GodotLaunchBridge.start(this)

        setContent {
            CEOSTheme {
                MainScreen()
            }
        }
    }
}
