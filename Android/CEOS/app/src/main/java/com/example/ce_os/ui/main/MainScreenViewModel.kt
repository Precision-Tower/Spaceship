package os.ce.node.ui.main

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import os.ce.node.data.BootstrapStatus
import os.ce.node.data.CeOsApi
import os.ce.node.data.CeOsStatus

data class MainUiState(
    val status: CeOsStatus? = null,
    val bootstrap: BootstrapStatus? = null,
    val loading: Boolean = true,
    val bootstrapBusy: Boolean = false,
    val bootstrapLeaseSeconds: Int = 0,
    val verification: String? = null,
    val error: String? = null
)

class MainScreenViewModel : ViewModel() {

    private val _state = MutableStateFlow(MainUiState())
    val state: StateFlow<MainUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val statusRequest = async {
                    CeOsApi.status()
                }

                val bootstrapRequest = async {
                    CeOsApi.bootstrapStatus()
                }

                val status = statusRequest.await()
                val bootstrap = bootstrapRequest.await()

                _state.value = _state.value.copy(
                    status = status,
                    bootstrap = bootstrap,
                    loading = false,
                    error = null
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = t.message ?: "CE-OS backend unavailable"
                )
            }
        }
    }

    fun setMode(mode: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                _state.value = _state.value.copy(
                    loading = true,
                    error = null
                )

                CeOsApi.setMode(mode)

                _state.value = _state.value.copy(
                    loading = false
                )

                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = t.message ?: "Mode request failed"
                )
            }
        }
    }

    fun enableBootstrap() {
        Log.i("CEOS-Control", "ViewModel enableBootstrap invoked")

        viewModelScope.launch(Dispatchers.IO) {
            try {
                Log.i("CEOS-Control", "ViewModel bootstrap coroutine started")
                _state.value = _state.value.copy(
                    bootstrapBusy = true,
                    error = null
                )

                val result = CeOsApi.enableBootstrap()

                if (!result.ok) {
                    error(result.error ?: "BOOTSTRAP enable failed")
                }

                _state.value = _state.value.copy(
                    bootstrapBusy = false,
                    bootstrapLeaseSeconds = result.leaseSeconds
                )

                refresh()
            } catch (t: Throwable) {
                Log.e("CEOS-Control", "BOOTSTRAP enable failed", t)

                _state.value = _state.value.copy(
                    bootstrapBusy = false,
                    error = t.message ?: "BOOTSTRAP enable failed"
                )
            }
        }
    }

    fun disableBootstrap() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                _state.value = _state.value.copy(
                    bootstrapBusy = true,
                    error = null
                )

                val result = CeOsApi.disableBootstrap()

                if (!result.ok) {
                    error(result.error ?: "BOOTSTRAP disable failed")
                }

                _state.value = _state.value.copy(
                    bootstrapBusy = false,
                    bootstrapLeaseSeconds = 0
                )

                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    bootstrapBusy = false,
                    error = t.message ?: "BOOTSTRAP disable failed"
                )
            }
        }
    }

    fun verifyPlatform() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = CeOsApi.verifyPlatform()

                _state.value = _state.value.copy(
                    verification =
                        if (result.ok) {
                            "VERIFIED: ${result.platformState.uppercase()}"
                        } else {
                            "FAILED: ${result.platformState.uppercase()}"
                        },
                    error = result.error
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    verification = "VERIFY FAILED",
                    error = t.message ?: "Platform verification failed"
                )
            }
        }
    }
}
