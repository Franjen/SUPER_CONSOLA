# LA SUPER CONSOLA

Biblioteca de juegos de escritorio para **Windows**, escrita en Python con Tkinter
y Pillow. Organiza juegos por sistema, muestra portadas y abre emuladores externos.
Incluye navegación por teclado y mando, e integración opcional con IGDB.

Esta importación corresponde a la aplicación de escritorio. **No es una APK ni una
versión para Android TV.** Los emuladores y juegos se instalan por separado.

## Organización

```text
Biblioteca/
  biblioteca.py                 Aplicación principal
  iniciar_biblioteca.bat         Lanzador original para Windows
  LA_SUPER_CONSOLA.exe           Binario original, sin validación de ejecución
  LA_SUPER_CONSOLA.ico           Icono
  config_igdb.example.json       Plantilla sin credenciales
  portadas/                     Imágenes incluidas en el paquete
historial/                      Tres respaldos originales con fecha
  README.md                     Explicación de los respaldos
docs/
  ARCHIVOS_IMPORTADOS.md         Procedencia, exclusiones y hashes
requirements.txt                Dependencia externa: Pillow
```

## Preparación en Windows

1. Instala Python 3 con Tcl/Tk y pip. Comprueba Tkinter con `py -m tkinter`.
2. Copia el contenido de `Biblioteca/` a `C:\Juegos\Biblioteca`.
   Esa ruta está fijada en el código y en el lanzador original.
3. Instala Pillow desde la raíz del repositorio:

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Coloca tus juegos en las subcarpetas por sistema de `C:\Juegos\ROMS`.
   Revisa el diccionario `SISTEMAS` en `biblioteca.py` para conocer las extensiones
   y rutas de emuladores. Entre ellos figuran Azahar, Project64, melonDS, mGBA y Snes9x;
   el código también contiene detección de Dolphin.
5. Ejecuta:

   ```powershell
   cd C:\Juegos\Biblioteca
   py biblioteca.py
   ```

También puedes usar `iniciar_biblioteca.bat` si el comando `python` está disponible.
La aplicación crea las carpetas de caché y portadas cuando son necesarias.

## Portadas de IGDB (opcional)

Copia `config_igdb.example.json` como `config_igdb.json` dentro de
`C:\Juegos\Biblioteca` y completa `client_id` y `client_secret` con tus propias
credenciales de Twitch/IGDB. No subas ese archivo a GitHub: está excluido por
`.gitignore`. Sin configuración de IGDB, puedes usar las portadas locales.

## Estado y validación

- Se conserva el código original; esta importación no cambia la lógica.
- Sintaxis de la aplicación y los respaldos comprobada con el analizador de Python.
- La interfaz, los mandos, los emuladores y el ejecutable requieren pruebas en Windows;
  no se han validado en este entorno Linux.
- El ZIP no especifica versiones de Python o Pillow ni contiene una suite de pruebas.
- La clase `Biblioteca` define `jugar_indice` dos veces: Python usa la última definición.
  Se deja documentado para una revisión posterior.
- No hay una licencia de software declarada en el paquete original.

Consulta [la procedencia y los hashes](docs/ARCHIVOS_IMPORTADOS.md).
