package os.ce.node

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import os.ce.node.data.CeOsApi

class CeOsTileService : TileService() {

    private val scope =
        CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onStartListening() {
        super.onStartListening()
        refreshTile()
    }

    override fun onClick() {
        super.onClick()

        scope.launch {
            try {
                val current = CeOsApi.status()

                val next =
                    if (current.requestedMode == "conserve")
                        "node"
                    else
                        "conserve"

                CeOsApi.setMode(next)

                refreshTile()
            } catch (_: Throwable) {
                qsTile?.apply {
                    state = Tile.STATE_UNAVAILABLE
                    label = "CE-OS"
                    subtitle = "OFFLINE"
                    updateTile()
                }
            }
        }
    }

    private fun refreshTile() {
        scope.launch {
            try {
                val status = CeOsApi.status()

                qsTile?.apply {
                    label = "CE-OS"
                    subtitle = status.requestedMode.uppercase()

                    state =
                        if (status.requestedMode == "node")
                            Tile.STATE_ACTIVE
                        else
                            Tile.STATE_INACTIVE

                    updateTile()
                }
            } catch (_: Throwable) {
                qsTile?.apply {
                    label = "CE-OS"
                    subtitle = "OFFLINE"
                    state = Tile.STATE_UNAVAILABLE
                    updateTile()
                }
            }
        }
    }
}
