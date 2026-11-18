package com.aztlan.route

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 56, 48, 40)
            setBackgroundColor(0xFFF5F7FA.toInt())
        }
        val scroll = ScrollView(this)
        scroll.addView(content)

        val title = TextView(this).apply {
            text = "AZTLÁN ROUTE"
            textSize = 27f
            setTextColor(0xFF152238.toInt())
            typeface = Typeface.DEFAULT_BOLD
        }
        content.addView(title)

        val subtitle = TextView(this).apply {
            text = "Aplicación móvil · versión 0.1.0-alpha01"
            textSize = 14f
            setTextColor(0xFF526174.toInt())
            setPadding(0, 8, 0, 28)
        }
        content.addView(subtitle)

        section(content, "Pruebas iniciales")
        status = TextView(this).apply {
            text = "Estado: aplicación instalada y ejecutándose en Android."
            textSize = 15f
            setTextColor(0xFF263548.toInt())
            setPadding(0, 12, 0, 20)
        }
        content.addView(status)

        section(content, "Acceso manual a proveedores")
        content.addView(providerButton("ChatGPT", "https://chatgpt.com/"))
        content.addView(providerButton("Google Gemini", "https://gemini.google.com/"))
        content.addView(providerButton("Claude", "https://claude.ai/"))
        content.addView(providerButton("Qwen", "https://chat.qwen.ai/"))
        content.addView(providerButton("DeepSeek", "https://chat.deepseek.com/"))

        section(content, "Alcance de esta versión")
        val note = TextView(this).apply {
            text = "Esta compilación valida el contenedor Android y la apertura del navegador externo. El inicio de sesión, CAPTCHA y MFA se realizan manualmente en el sitio oficial. Esta versión todavía no envía mensajes a modelos ni almacena claves API."
            textSize = 14f
            setTextColor(0xFF526174.toInt())
            setPadding(0, 8, 0, 18)
        }
        content.addView(note)

        val footer = TextView(this).apply {
            text = "Siguiente integración: catálogo de proveedores, almacenamiento local cifrado y conexiones API autorizadas."
            textSize = 13f
            setTextColor(0xFF526174.toInt())
            setPadding(0, 12, 0, 0)
        }
        content.addView(footer)
        setContentView(scroll)
    }

    private fun section(parent: LinearLayout, label: String) {
        parent.addView(TextView(this).apply {
            text = label
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(0xFF152238.toInt())
            setPadding(0, 20, 0, 8)
        })
    }

    private fun providerButton(label: String, url: String): Button =
        Button(this).apply {
            text = "Abrir $label"
            isAllCaps = false
            gravity = Gravity.CENTER
            setOnClickListener {
                try {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    status.text = "Estado: se solicitó abrir $label en el navegador. Completa el acceso manualmente."
                } catch (_: Exception) {
                    status.text = "No se encontró un navegador compatible para abrir $label."
                }
            }
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = 8 }
        }
}
