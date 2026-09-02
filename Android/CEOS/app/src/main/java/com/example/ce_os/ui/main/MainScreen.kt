package os.ce.node.ui.main

import android.util.Log
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay

@Composable
fun MainScreen(
    vm: MainScreenViewModel = viewModel()
) {
    val ui by vm.state.collectAsState()

    LaunchedEffect(Unit) {
        while (true) {
            delay(5000)
            vm.refresh()
        }
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text(
                text = "CE-OS",
                style = MaterialTheme.typography.headlineLarge
            )

            Text(
                text = "PIXEL NODE",
                style = MaterialTheme.typography.titleMedium
            )

            if (ui.loading && ui.status == null) {
                CircularProgressIndicator()
            }

            ui.error?.let {
                Card(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("CE-OS control error")
                        Text(it)
                    }
                }
            }

            ui.status?.let { status ->
                Text(
                    "MODE",
                    style = MaterialTheme.typography.titleMedium
                )

                StatusRow(
                    "Requested",
                    status.requestedMode.uppercase()
                )

                StatusRow(
                    "Effective",
                    status.effectiveMode.uppercase()
                )

                Text(
                    "USB",
                    style = MaterialTheme.typography.titleMedium
                )

                StatusRow(
                    "Requested",
                    status.requestedUsbMode.uppercase()
                )

                StatusRow(
                    "Hardware",
                    when (status.usbMode) {
                        "bootstrap" -> "CE-OS BOOTSTRAP"
                        "none" -> "ANDROID"
                        else -> status.usbMode.uppercase()
                    }
                )

                StatusRow(
                    "Guardian",
                    if (
                        status.requestedMode == status.effectiveMode
                    ) {
                        "PERMITTED"
                    } else {
                        "DENIED"
                    }
                )

                StatusRow(
                    "Platform",
                    when (status.platformState) {
                        "ok" -> "LOCKED"
                        else -> status.platformState.uppercase()
                    }
                )

                StatusRow(
                    "Power",
                    status.powerState.uppercase()
                )

                StatusRow(
                    "Battery",
                    if (status.battery == "unknown")
                        "UNKNOWN"
                    else
                        "${status.battery}%"
                )

                StatusRow(
                    "Battery Temp",
                    if (status.batteryTempC == "unknown")
                        "UNKNOWN"
                    else
                        "${status.batteryTempC} C"
                )

                StatusRow(
                    "Thermal",
                    status.thermalState.uppercase()
                )

                StatusRow(
                    "Compute",
                    if (status.allowCompute)
                        "ALLOWED"
                    else
                        "BLOCKED"
                )

                if (status.reasons.isNotEmpty()) {
                    Text(
                        "Guardian: ${status.reasons.joinToString(", ")}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                if (status.timestamp.isNotBlank()) {
                    Text(
                        "Telemetry: ${status.timestamp}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Spacer(Modifier.height(4.dp))

            val effectiveMode = ui.status?.effectiveMode

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (effectiveMode == "node") {
                    Button(
                        modifier = Modifier.weight(1f),
                        onClick = { vm.setMode("node") }
                    ) {
                        Text("NODE")
                    }
                } else {
                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        onClick = { vm.setMode("node") }
                    ) {
                        Text("NODE")
                    }
                }

                if (effectiveMode == "conserve") {
                    Button(
                        modifier = Modifier.weight(1f),
                        onClick = { vm.setMode("conserve") }
                    ) {
                        Text("CONSERVE")
                    }
                } else {
                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        onClick = { vm.setMode("conserve") }
                    ) {
                        Text("CONSERVE")
                    }
                }
            }

            val bootstrapActive =
                ui.bootstrap?.active == true ||
                    ui.status?.usbMode == "bootstrap"

            if (bootstrapActive) {
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !ui.bootstrapBusy,
                    onClick = { vm.disableBootstrap() }
                ) {
                    Text("RETURN TO ANDROID")
                }

                Text(
                    "BOOTSTRAP lease active. Automatic recovery remains armed.",
                    style = MaterialTheme.typography.bodySmall
                )
            } else {
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !ui.bootstrapBusy,
                    onClick = {
                        Log.i("CEOS-Control", "ENABLE BOOTSTRAP button tapped")
                        vm.enableBootstrap()
                    }
                ) {
                    Text("ENABLE BOOTSTRAP")
                }

                Text(
                    "Experimental 30 second lease. USB automatically returns to Android.",
                    style = MaterialTheme.typography.bodySmall
                )
            }

            if (ui.bootstrapBusy) {
                CircularProgressIndicator()
            }

            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = { vm.verifyPlatform() }
            ) {
                Text("VERIFY PLATFORM")
            }

            ui.verification?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.titleMedium
                )
            }

            OutlinedButton(
                modifier = Modifier.fillMaxWidth(),
                onClick = { vm.refresh() }
            ) {
                Text("REFRESH")
            }
        }
    }
}

@Composable
private fun StatusRow(
    name: String,
    value: String
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(name)
            Text(
                value,
                style = MaterialTheme.typography.titleMedium
            )
        }
    }
}
