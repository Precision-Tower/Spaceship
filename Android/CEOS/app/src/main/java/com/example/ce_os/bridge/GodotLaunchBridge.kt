package os.ce.node.bridge

import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.FileProvider
import java.io.File
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.InetAddress
import java.net.ServerSocket
import java.util.concurrent.Executors

object GodotLaunchBridge {

    private const val TAG = "CEOS-GodotBridge"
    private const val PORT = 8766

    private const val GODOT_PACKAGE =
        "org.godotengine.editor.v4"

    private const val GODOT_ACTIVITY =
        "org.godotengine.editor.ProjectManager"

    private const val PROJECT =
        "/sdcard/CE-OS/OperatorShell"

    private var server: ServerSocket? = null

    private val executor =
        Executors.newSingleThreadExecutor()

    @Synchronized
    fun start(context: Context) {
        if (server != null) {
            return
        }

        val appContext = context.applicationContext

        executor.execute {
            try {
                val socket = ServerSocket(
                    PORT,
                    8,
                    InetAddress.getByName("127.0.0.1")
                )

                server = socket

                Log.i(
                    TAG,
                    "Listening on 127.0.0.1:$PORT"
                )

                while (!socket.isClosed) {
                    val client = socket.accept()

                    client.use {
                        val reader =
                            BufferedReader(
                                InputStreamReader(
                                    it.getInputStream()
                                )
                            )

                        val raw =
                            reader.readLine()
                                ?: ""

                        val response =
                            handle(
                                appContext,
                                raw
                            )

                        it.getOutputStream().bufferedWriter().use { writer ->
                            writer.write(
                                response.toString()
                            )
                            writer.newLine()
                            writer.flush()
                        }
                    }
                }
            } catch (t: Throwable) {
                Log.e(
                    TAG,
                    "Launch bridge stopped",
                    t
                )

                server = null
            }
        }
    }

    private fun handle(
        context: Context,
        raw: String
    ): JSONObject {

        return try {
            val request =
                JSONObject(raw)

            when (
                request.optString(
                    "operation"
                )
            ) {
                "health" ->
                    JSONObject()
                        .put("ok", true)
                        .put(
                            "service",
                            "godot-launch-bridge"
                        )

                "godot.open-project" ->
                    openProject(context)

                else ->
                    JSONObject()
                        .put("ok", false)
                        .put(
                            "error",
                            "unsupported operation"
                        )
            }
        } catch (t: Throwable) {
            JSONObject()
                .put("ok", false)
                .put(
                    "error",
                    t.message
                        ?: t.javaClass.simpleName
                )
        }
    }

    private fun openProject(
        context: Context
    ): JSONObject {

        val projectFile =
            "$PROJECT/project.godot"

        val projectUri =
            FileProvider.getUriForFile(
                context,
                "os.ce.node.fileprovider",
                File(projectFile)
            )

        val intent =
            Intent(Intent.ACTION_VIEW).apply {
                setClassName(
                    GODOT_PACKAGE,
                    GODOT_ACTIVITY
                )

                setDataAndType(
                    projectUri,
                    "application/octet-stream"
                )

                addCategory(
                    Intent.CATEGORY_DEFAULT
                )

                addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or
                        Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            }

        context.startActivity(intent)

        Log.i(
            TAG,
            "Requested Godot project open: $projectFile"
        )

        return JSONObject()
            .put("ok", true)
            .put(
                "operation",
                "godot.open-project"
            )
            .put(
                "launch_requested",
                true
            )
            .put(
                "project",
                projectFile
            )
    }

}
