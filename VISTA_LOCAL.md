# Aplicación en ejecución para vistazos de desarrollo

Petición del usuario: mantener una vista local de la aplicación, preferiblemente en una pestaña del IDE, como apoyo secundario que no retrase el desarrollo ni exija pruebas continuadas.

Ejecutar desde la raíz:

```powershell
.venv/Scripts/python.exe scripts/preview_local.py
```

Abrir http://127.0.0.1:8765 en el navegador integrado del IDE cuando esté disponible. Es la aplicación funcionando, con entrada automática a una campaña de demostración. Si no hay control de pestañas disponible, basta dejar el servidor activo y el enlace accesible; no instalar extensiones ni pedir configuración al usuario por este objetivo secundario.

La cabecera identifica el entorno: datos temporales en memoria y director simulado. No usa Anthropic ni Firebase; las tipografías de la interfaz pueden cargarse desde Google Fonts. El servidor escucha solo en loopback. No introducir datos personales, manuales originales ni campañas reales: reiniciarlo descarta los datos temporales. La semilla usa exclusivamente reglas y ficción de ejemplo propias; no certifica un sistema ni una aventura autónoma terminada.

Los recursos de interfaz se sirven desde los archivos actuales; las modificaciones de Python requieren reiniciar este proceso aislado. Comprobar antes si el puerto ya está activo y reutilizarlo. No abrir otra ventana ni otro servidor por cada entrega. Los vistazos no sustituyen las comprobaciones técnicas ni los hitos excepcionales de prueba personal de PRODUCTO.md.
