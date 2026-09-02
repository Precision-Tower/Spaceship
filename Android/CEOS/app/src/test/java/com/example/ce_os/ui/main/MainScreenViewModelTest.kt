package os.ce.node.ui.main

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MainScreenViewModelTest {

    @Test
    fun mainUiState_defaults_are_safe() {
        val state = MainUiState()

        assertNull(state.status)
        assertNull(state.bootstrap)
        assertTrue(state.loading)
        assertFalse(state.bootstrapBusy)
        assertEquals(0, state.bootstrapLeaseSeconds)
        assertNull(state.verification)
        assertNull(state.error)
    }

    @Test
    fun mainUiState_canRepresentBootstrapLease() {
        val state = MainUiState(
            loading = false,
            bootstrapBusy = true,
            bootstrapLeaseSeconds = 30
        )

        assertFalse(state.loading)
        assertTrue(state.bootstrapBusy)
        assertEquals(30, state.bootstrapLeaseSeconds)
    }
}
