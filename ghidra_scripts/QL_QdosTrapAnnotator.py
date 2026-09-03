# @runtime Jython
# -*- coding: utf-8 -*-
# QL_QdosTrapAnnotator.py
#
# NOTA (Ghidra 12.0+): desde Ghidra 12, los scripts .py se ejecutan por
# defecto con PyGhidra (CPython 3 vía jpype), que requiere un Python 3
# instalado en el sistema y arrancar Ghidra con pyghidraRun. Este script
# esta escrito para el motor Jython clasico (API GhidraScript / FlatAPI en
# estilo Jython 2), asi que la linea "# @runtime Jython" de arriba es
# OBLIGATORIA y debe ser la primera linea del fichero: le dice al Script
# Manager que lo ejecute con el interprete Jython integrado en vez de
# intentar usar PyGhidra. Si la borras o la mueves, veras el error:
#   "Ghidra was not started with PyGhidra. Python is not available"
#
# Primer modulo de un futuro "Ghidra QL module" para ingenieria inversa de
# ROMs de la Sinclair QL (Qdos, 68008): CPU 68008, sistema operativo Qdos.
#
# Que hace este script:
#   1. Recorre todas las instrucciones del programa ya desensamblado.
#   2. Para cada "TRAP #n" (n = 0..4), busca hacia atras la ultima
#      instruccion que carga un valor inmediato en D0 (la "clave" de la
#      llamada Qdos, normalmente un MOVEQ #n,D0).
#   3. Busca esa clave en las tablas de:
#        - Manager Traps      (TRAP #1)  -> tabla TRAP1
#        - I/O Management Traps (TRAP #2) -> tabla TRAP2
#        - I/O Traps          (TRAP #3)  -> tabla TRAP3
#      y anade un comentario EOL con el nombre Qdos (MT.xxx / IO.xxx /
#      SD.xxx / FS.xxx) y una breve descripcion de que hace la llamada.
#   4. Ademas detecta el patron de llamada a rutinas vectorizadas de la ROM:
#        MOVE.W #vector,An
#        JSR (An)            (o JSR $4000(An) para las que usan ese offset)
#      y anota el JSR con el nombre/uso del vector (tabla VECTORS).
#   5. Crea un bookmark "QDOS" en cada trap/vector reconocido, para poder
#      navegar rapido por la ventana de Bookmarks.
#   6. Reconoce y etiqueta los ACCESOS A LAS VARIABLES DE SISTEMA (SV_xxx,
#      seccion 18.2 de la QL Technical Guide): busca patrones "offset(Rn)"
#      donde Rn es un registro que el script considera que contiene el
#      puntero base de las variables de sistema, y anade un comentario EOL
#      con el nombre SV_xxx y su significado. Ese registro puede ser:
#        - A6, por convencion, en rutinas de driver/tarea (fisica o de
#          acceso) y en la mayoria de rutinas vectorizadas (asi lo dice el
#          propio manual: "A6 pointer to system variables").
#        - A0, justo despues de un TRAP #1 D0=$00 (MT.INF), que siempre
#          devuelve ahi el puntero a las variables de sistema.
#      Al arrancar, el script pregunta que convencion(es) quieres asumir.
#      Tambien crea bookmarks de categoria "QDOS-SV" en cada acceso.
#
# Como usarlo:
#   - Carga el binario (ROM de tarjeta de expansion QL, imagen de Qdos, etc.)
#     con el lenguaje 68000:BE:32:default (el 68008 es un subconjunto del
#     68000 a nivel de ISA/desensamblado; solo cambia el bus de datos).
#   - Si el binario esta mapeado en un slot de expansion, recuerda que en la
#     QL real ese codigo se ejecuta con PC-relative addressing desde su base
#     fisica (p.ej. $C0000 para el primer slot): ajusta la base de carga en
#     Ghidra (Options > Memory Map) antes de analizar si quieres que las
#     direcciones absolutas del comentario coincidan con las del hardware.
#   - Copia este fichero a tu carpeta de scripts de Ghidra (Window > Script
#     Manager > "Bundle Manager", o simplemente a ~/ghidra_scripts) y
#     ejecutalo desde el Script Manager (categoria QL.QDOS).
#
# Limitaciones de esta primera version (a mejorar en pasos siguientes):
#   - La busqueda hacia atras del valor de D0 es un heuristico simple: para
#     en el primer branch/llamada/retorno que encuentra, o tras un numero
#     maximo de instrucciones. Si D0 se calcula dinamicamente (tabla de
#     saltos, parametro de funcion, etc.) el script marca la clave como
#     "no determinada estaticamente" en vez de inventarsela.
#   - No sigue todavia los saltos (JMP/Bcc) hacia atras para encontrar el
#     MOVEQ en un bloque distinto; solo mira instrucciones "en linea recta"
#     anteriores a la TRAP dentro del mismo flujo.
#   - No decodifica los sub-codigos de IO.OPEN en D3 (old/shared/new/...)
#     ni los parametros de MT.IPCOM; queda para una version 2.
#   - El reconocimiento de variables de sistema (SV_xxx) asume que el/los
#     registro(s) elegidos mantienen el puntero SV_BASE de forma sencilla:
#     para el registro persistente (tipicamente A6) NO se comprueba que de
#     verdad siga apuntando ahi durante toda la rutina (es la convencion
#     documentada, pero si tu codigo reutiliza A6 para otra cosa dentro de
#     la misma funcion, el script se equivocara). Revisa los resultados con
#     sentido critico, sobre todo en funciones largas.
#   - OJO: esta tabla es para las variables de SISTEMA (SV_xxx). Las
#     variables de trabajo de SuperBASIC (BV_xxx, seccion 18.3) tambien se
#     acceden via A6, pero es un A6 *distinto* (base del area de trabajo de
#     SuperBASIC, no de las variables de sistema). Si vas a analizar
#     extensiones de SuperBASIC en vez de ROMs de controlador, NO actives
#     el reconocimiento por A6 para SV_xxx o tendras falsos positivos (de
#     momento no hay tabla BV_xxx en este script; queda para otra iteracion
#     si la necesitas).
#
#@category QL.QDOS
#@menupath Analysis.QL.Anotar traps y vectores QDOS

from ghidra.program.model.listing import CodeUnit
from ghidra.program.model.scalar import Scalar


# ---------------------------------------------------------------------------
# Tablas de claves Qdos (nombre, descripcion breve)
# Fuente: QL Technical Guide, secciones 13.0-16.0 y 18.14-18.15
# ---------------------------------------------------------------------------

TRAP1 = {
    0x00: ("MT.INF",   "Informacion del sistema: job ID actual y version de Qdos"),
    0x01: ("MT.CJOB",  "Crea un job en el area de programas transitorios"),
    0x02: ("MT.JINF",  "Devuelve el estado/informacion de un job"),
    0x04: ("MT.RJOB",  "Elimina un job inactivo del area transitoria"),
    0x05: ("MT.FRJOB", "Fuerza la eliminacion de un job (activo o no)"),
    0x06: ("MT.FREE",  "Busca el mayor hueco libre contiguo en el area transitoria"),
    0x07: ("MT.TRAPV", "Fija la tabla de redireccion de traps/excepciones de un job"),
    0x08: ("MT.SUSJB", "Suspende un job"),
    0x09: ("MT.RELJB", "Libera (reactiva) un job suspendido"),
    0x0A: ("MT.ACTIV", "Activa un job"),
    0x0B: ("MT.PRIOR", "Cambia la prioridad de un job"),
    0x0C: ("MT.ALLOC", "Reserva espacio en un heap generico"),
    0x0D: ("MT.LNKFR", "Devuelve un espacio libre a un heap"),
    0x0E: ("MT.ALRES", "Reserva espacio en el area de procedimientos residentes"),
    0x0F: ("MT.RERES", "Libera espacio del area de procedimientos residentes"),
    0x10: ("MT.DMODE", "Fija o lee el modo de pantalla (4/8 colores)"),
    0x11: ("MT.IPCOM", "Envia un comando al IPC (teclado, sonido, reloj...)"),
    0x12: ("MT.BAUD",  "Fija la velocidad (baud rate) del puerto serie"),
    0x13: ("MT.RCLCK", "Lee el reloj en tiempo real"),
    0x14: ("MT.SCLCK", "Fija el reloj en tiempo real"),
    0x15: ("MT.ACLCK", "Ajusta el reloj en tiempo real"),
    0x16: ("MT.ALBAS", "Reserva/amplia el area de programa de SuperBASIC"),
    0x17: ("MT.REBAS", "Libera espacio del area de SuperBASIC"),
    0x18: ("MT.ALCHP", "Reserva espacio en el heap comun (common heap)"),
    0x19: ("MT.RECHP", "Libera espacio del heap comun"),
    0x1A: ("MT.LXINT", "Enlaza una rutina de servicio de interrupcion externa"),
    0x1B: ("MT.RXINT", "Desenlaza una rutina de interrupcion externa"),
    0x1C: ("MT.LPOLL", "Enlaza una tarea de sondeo (poll) a 50/60Hz"),
    0x1D: ("MT.RPOLL", "Desenlaza una tarea de sondeo a 50/60Hz"),
    0x1E: ("MT.LSCHD", "Enlaza una tarea del bucle del planificador (scheduler)"),
    0x1F: ("MT.RSCHD", "Desenlaza una tarea del planificador"),
    0x20: ("MT.LIOD",  "Enlaza un controlador (driver) de dispositivo de E/S"),
    0x21: ("MT.RIOD",  "Desenlaza un controlador de dispositivo de E/S"),
    0x22: ("MT.LDD",   "Enlaza un controlador de directorio (sistema de ficheros)"),
    0x23: ("MT.RDD",   "Desenlaza un controlador de directorio"),
}

TRAP2 = {
    0x01: ("IO.OPEN",  "Abre un canal de E/S a un dispositivo o fichero"),
    0x02: ("IO.CLOSE", "Cierra un canal de E/S"),
    0x03: ("IO.FORMT", "Formatea un soporte (medium) sectorizado"),
    0x04: ("IO.DELET", "Borra un fichero"),
}

TRAP3 = {
    0x00: ("IO.PEND",  "Comprueba si hay entrada pendiente en un canal"),
    0x01: ("IO.FBYTE", "Lee un byte de un canal"),
    0x02: ("IO.FLINE", "Lee una linea de bytes terminada en newline"),
    0x03: ("IO.FSTRG", "Lee una cadena de bytes"),
    0x04: ("IO.EDLIN", "Edita una linea de caracteres (solo canal de consola)"),
    0x05: ("IO.SBYTE", "Envia un byte a un canal"),
    0x07: ("IO.SSTRG", "Envia una cadena de bytes"),
    0x09: ("SD.EXTOP", "Invoca una operacion de pantalla extendida definida por el usuario"),
    0x0A: ("SD.PXENQ", "Devuelve tamano de ventana y posicion del cursor (coords. de pixel)"),
    0x0B: ("SD.CHENQ", "Devuelve tamano de ventana y posicion del cursor (coords. de caracter)"),
    0x0C: ("SD.BORDR", "Fija el ancho y color del borde de la ventana"),
    0x0D: ("SD.WDEF",  "Redefine forma/posicion de una ventana"),
    0x0E: ("SD.CURE",  "Activa el cursor"),
    0x0F: ("SD.CURS",  "Suprime el cursor"),
    0x10: ("SD.POS",   "Posiciona el cursor de forma absoluta (coords. de caracter)"),
    0x11: ("SD.TAB",   "Tabula el cursor horizontalmente"),
    0x12: ("SD.NL",    "Nueva linea (newline)"),
    0x13: ("SD.PCOL",  "Cursor a la columna anterior"),
    0x14: ("SD.NCOL",  "Cursor a la columna siguiente"),
    0x15: ("SD.PROW",  "Cursor a la fila anterior"),
    0x16: ("SD.NROW",  "Cursor a la fila siguiente"),
    0x17: ("SD.PIXP",  "Posiciona el cursor usando coordenadas de pixel"),
    0x18: ("SD.SCROL", "Desplaza (scroll) toda la ventana"),
    0x19: ("SD.SCRTP", "Desplaza la parte superior de la ventana"),
    0x1A: ("SD.SCRBT", "Desplaza la parte inferior de la ventana"),
    0x1B: ("SD.PAN",   "Desplaza (pan) toda la ventana horizontalmente"),
    0x1E: ("SD.PANLN", "Desplaza la linea del cursor"),
    0x1F: ("SD.PANRT", "Desplaza el extremo derecho de la linea del cursor"),
    0x20: ("SD.CLEAR", "Borra toda la ventana"),
    0x21: ("SD.CLRTP", "Borra la parte superior de la ventana"),
    0x22: ("SD.CLRBT", "Borra la parte inferior de la ventana"),
    0x23: ("SD.CLRLN", "Borra la linea del cursor"),
    0x24: ("SD.CLRRT", "Borra el extremo derecho de la linea del cursor"),
    0x25: ("SD.FOUNT", "Fija o restaura el juego de caracteres (fount)"),
    0x26: ("SD.RECOL", "Recolorea una ventana"),
    0x27: ("SD.SETPA", "Fija el color de papel (fondo)"),
    0x28: ("SD.SETST", "Fija el color de franja (strip)"),
    0x29: ("SD.SETIN", "Fija el color de tinta (ink)"),
    0x2A: ("SD.SETFL", "Activa/desactiva el parpadeo (flash) por hardware"),
    0x2B: ("SD.SETUL", "Activa/desactiva el subrayado"),
    0x2C: ("SD.SETMD", "Fija el modo de escritura/dibujo de caracteres"),
    0x2D: ("SD.SETSZ", "Fija tamano y espaciado de caracteres"),
    0x2E: ("SD.FILL",  "Rellena un bloque rectangular de la ventana"),
    0x2F: ("SD.DONL",  "Ejecuta el newline pendiente"),
    0x30: ("SD.POINT", "Dibuja un punto"),
    0x31: ("SD.LINE",  "Dibuja una linea"),
    0x32: ("SD.ARC",   "Dibuja un arco"),
    0x33: ("SD.ELIPS", "Dibuja una elipse"),
    0x34: ("SD.SCALE", "Fija la escala grafica"),
    0x35: ("SD.FLOOD", "Activa/desactiva el relleno de area (flood fill)"),
    0x36: ("SD.GCUR",  "Mueve el cursor grafico"),
    0x37: ("SD.ROP",   "Operaciones raster sobre coordenadas"),
    0x38: ("SD.DOT",   "Dibuja puntos en coordenadas de pixel"),
    0x39: ("SD.LIN",   "Dibuja lineas en coordenadas de pixel"),
    0x40: ("FS.CHECK", "Comprueba que todas las operaciones pendientes de un fichero han terminado"),
    0x41: ("FS.FLUSH", "Vuelca (flush) los buffers de escritura de un fichero"),
    0x42: ("FS.POSAB", "Posiciona el puntero de fichero de forma absoluta"),
    0x43: ("FS.POSRE", "Posiciona el puntero de fichero de forma relativa"),
    0x45: ("FS.MDINF", "Obtiene informacion del soporte (medium) montado"),
    0x46: ("FS.HEADS", "Fija la cabecera del fichero"),
    0x47: ("FS.HEADR", "Lee la cabecera del fichero"),
    0x48: ("FS.LOAD",  "Carga un fichero en memoria"),
    0x49: ("FS.SAVE",  "Guarda un fichero desde memoria"),
}

# Rutinas vectorizadas (tabla en ROM a partir de $C0). Se llaman como:
#   MOVE.W vector,An
#   JSR (An)
# o, para las marcadas con offset $4000, como:
#   MOVE.W vector,An
#   JSR $4000(An)
VECTORS = {
    0x02:  ("UT.LINK",   "Enlaza un elemento en una lista enlazada"),
    0x04:  ("UT.UNLNK",  "Desenlaza un elemento de una lista enlazada"),
    0xC0:  ("MM.ALCHP",  "Reserva espacio en el heap comun (modo supervisor)"),
    0xC2:  ("MM.RECHP",  "Libera espacio del heap comun (modo supervisor)"),
    0xC4:  ("UT.WINDW",  "Crea una ventana consola/pantalla a partir de un nombre de dispositivo"),
    0xC6:  ("UT.CON",    "Crea una ventana de consola"),
    0xC8:  ("UT.SCR",    "Crea una ventana de pantalla"),
    0xCA:  ("UT.ERRO",   "Escribe un mensaje de error en el canal 0"),
    0xCC:  ("UT.ERR",    "Escribe un mensaje de error en el canal indicado"),
    0xCE:  ("UT.MINT",   "Convierte un entero a ASCII y lo envia a un canal"),
    0xD0:  ("UT.MTEXT",  "Envia un mensaje de texto a un canal"),
    0xD8:  ("MM.ALLOC",  "Reserva un area dentro de un heap (modo supervisor)"),
    0xDA:  ("MM.LNKFR",  "Devuelve un area libre a un heap (modo supervisor)"),
    0xDC:  ("IO.QSET",   "Inicializa una cola (queue)"),
    0xDE:  ("IO.QTEST",  "Comprueba el estado de una cola"),
    0xE0:  ("IO.QIN",    "Introduce un byte en una cola"),
    0xE2:  ("IO.QOUT",   "Extrae un byte de una cola"),
    0xE4:  ("IO.QEOF",   "Introduce marca de fin de fichero en una cola"),
    0xE6:  ("UT.CSTR",   "Compara dos cadenas"),
    0xE8:  ("IO.SERQ",   "Manejo directo de E/S serie via colas (llamada con offset $4000)"),
    0xEA:  ("IO.SERIO",  "Manejo generico de E/S serie via rutinas de usuario (llamada con offset $4000)"),
    0xEC:  ("CN.DATE",   "Obtiene fecha y hora en ASCII"),
    0xEE:  ("CN.DAY",    "Obtiene el dia de la semana en ASCII"),
    0xF0:  ("CN.FTOD",   "Convierte coma flotante a ASCII decimal"),
    0xF2:  ("CN.ITOD",   "Convierte entero a ASCII decimal"),
    0xF4:  ("CN.ITOBB",  "Convierte byte a ASCII binario"),
    0xF6:  ("CN.ITOBW",  "Convierte word a ASCII binario"),
    0xF8:  ("CN.ITOBL",  "Convierte long a ASCII binario"),
    0xFA:  ("CN.ITOHB",  "Convierte byte a ASCII hexadecimal"),
    0xFC:  ("CN.ITOHW",  "Convierte word a ASCII hexadecimal"),
    0xFE:  ("CN.ITOHL",  "Convierte long a ASCII hexadecimal"),
    0x100: ("CN.DTOF",   "Convierte ASCII decimal a coma flotante"),
    0x102: ("CN.DTOI",   "Convierte ASCII decimal a entero"),
    0x104: ("CN.BTOIB",  "Convierte ASCII binario a byte"),
    0x106: ("CN.BTOIW",  "Convierte ASCII binario a word"),
    0x108: ("CN.BTOIL",  "Convierte ASCII binario a long"),
    0x10A: ("CN.HTOIB",  "Convierte ASCII hexadecimal a byte"),
    0x10C: ("CN.HTOIW",  "Convierte ASCII hexadecimal a word"),
    0x10E: ("CN.HTOIL",  "Convierte ASCII hexadecimal a long"),
    0x110: ("BP.INIT",   "Enlaza procedimientos/funciones en codigo maquina en la tabla de nombres de SuperBASIC"),
    0x112: ("CA.GTINT",  "Obtiene parametros enteros (16 bit) en la pila aritmetica"),
    0x114: ("CA.GTFP",   "Obtiene parametros en coma flotante en la pila aritmetica"),
    0x116: ("CA.GTSTR",  "Obtiene parametros de tipo cadena en la pila aritmetica"),
    0x118: ("CA.GTLIN",  "Obtiene parametros como enteros largos (32 bit) en la pila aritmetica"),
    0x11A: ("BV.CHRIX",  "Reserva espacio en la pila aritmetica (RI stack)"),
    0x11C: ("RI.EXEC",   "Ejecuta una operacion del interprete aritmetico"),
    0x11E: ("RI.EXECB",  "Ejecuta una lista de operaciones del interprete aritmetico"),
    0x120: ("BP.LET",    "Asigna el valor en la pila aritmetica a una entrada de la tabla de nombres"),
    0x122: ("IO.NAME",   "Decodifica un nombre de dispositivo"),
    0x124: ("MD.READ",   "Lee un sector de Microdrive (llamada con offset $4000)"),
    0x126: ("MD.WRITE",  "Escribe un sector de Microdrive (llamada con offset $4000)"),
    0x128: ("MD.VERIN",  "Verifica un sector de Microdrive (llamada con offset $4000)"),
    0x12A: ("MD.SECTR",  "Lee la cabecera de un sector de Microdrive (llamada con offset $4000)"),
}

# Vectores que se invocan con "JSR $4000(An)" en vez de "JSR (An)"
VECTORS_OFFSET_4000 = set([0xE8, 0xEA, 0x124, 0x126, 0x128, 0x12A])


# ---------------------------------------------------------------------------
# Variables de sistema (SV_xxx) - QL Technical Guide, seccion 18.2.
# offset (desde la base de variables de sistema) -> (nombre, descripcion)
# ---------------------------------------------------------------------------

SVVARS = {
    0x00:  ("SV_IDENT", "Palabra de identificacion del bloque de variables de sistema"),
    0x04:  ("SV_CHEAP", "Puntero a la base del area de heap comun"),
    0x08:  ("SV_CHPFR", "Puntero al primer espacio libre del heap comun"),
    0x0C:  ("SV_FREE",  "Puntero a la base del area libre (buffers de slave blocks)"),
    0x10:  ("SV_BASIC", "Puntero a la base del area de SuperBASIC"),
    0x14:  ("SV_TRNSP", "Puntero a la base del area de programas transitorios"),
    0x18:  ("SV_TRNFR", "Puntero al primer espacio libre del area transitoria"),
    0x1C:  ("SV_RESPR", "Puntero a la base del area de procedimientos residentes"),
    0x20:  ("SV_RAMT",  "Puntero al tope de la RAM (+1)"),
    0x2E:  ("SV_RAND",  "Numero aleatorio"),
    0x30:  ("SV_POLLM", "Contador de interrupciones de poll (50/60Hz) perdidas"),
    0x32:  ("SV_TVMOD", "Distinto de cero si la pantalla es de tipo TV"),
    0x33:  ("SV_SCRST", "Estado de la pantalla (0 = activa)"),
    0x34:  ("SV_MCSTA", "Valor actual del registro de control de pantalla"),
    0x35:  ("SV_PCINT", "Valor actual del registro de control/mascara de interrupciones"),
    0x37:  ("SV_NETNR", "Numero de estacion de red"),
    0x38:  ("SV_I2LST", "Puntero a la lista de drivers de interrupcion externa (nivel 2)"),
    0x3C:  ("SV_PLIST", "Puntero a la lista de tareas de poll (sondeo 50/60Hz)"),
    0x40:  ("SV_SHLST", "Puntero a la lista de tareas del bucle del planificador"),
    0x44:  ("SV_DRLST", "Puntero a la lista de controladores de dispositivo de E/S"),
    0x48:  ("SV_DDLST", "Puntero a la lista de controladores de directorio (ficheros)"),
    0x4C:  ("SV_KEYQ",  "Puntero a una cola de teclado"),
    0x50:  ("SV_TRAPV", "Puntero a la tabla de redireccion de traps/excepciones"),
    0x54:  ("SV_BTPNT", "Puntero a la entrada de slave block asignada mas reciente"),
    0x58:  ("SV_BTBAS", "Puntero a la base de la tabla de slave blocks"),
    0x5C:  ("SV_BTTOP", "Puntero al tope de la tabla de slave blocks"),
    0x60:  ("SV_JBTAG", "Valor actual de la etiqueta (tag) de job"),
    0x62:  ("SV_JBMAX", "Numero de job mas alto actualmente en uso"),
    0x64:  ("SV_JBPNT", "Puntero a la entrada actual de la tabla de jobs"),
    0x68:  ("SV_JBBAS", "Puntero a la base de la tabla de jobs"),
    0x6C:  ("SV_JBTOP", "Puntero al tope de la tabla de jobs"),
    0x70:  ("SV_CHTAG", "Valor actual de la etiqueta (tag) de canal"),
    0x72:  ("SV_CHMAX", "Numero de canal mas alto actualmente en uso"),
    0x74:  ("SV_CHPNT", "Puntero al ultimo canal comprobado"),
    0x78:  ("SV_CHBAS", "Puntero a la base de la tabla de canales"),
    0x7C:  ("SV_CHTOP", "Puntero al tope de la tabla de canales"),
    0x88:  ("SV_CAPS",  "Estado de CAPS LOCK"),
    0x8A:  ("SV_ARBUF", "Buffer de auto-repeticion de teclado"),
    0x8C:  ("SV_ARDEL", "Retardo antes de iniciar la auto-repeticion de tecla"),
    0x8E:  ("SV_ARFRQ", "Intervalo entre repeticiones (1/frecuencia) de auto-repeticion"),
    0x90:  ("SV_ARCNT", "Contador de auto-repeticion"),
    0x92:  ("SV_CQCH",  "Codigo de caracter para cambiar de cola de teclado (change queue)"),
    0x96:  ("SV_SOUND", "Estado del generador de sonido"),
    0x98:  ("SV_SER1C", "Direccion de la cola de recepcion del canal serie 1"),
    0x9C:  ("SV_SER2C", "Direccion de la cola de recepcion del canal serie 2"),
    0xA0:  ("SV_TMODE", "Modo de transmision del ZX8302 (incluye velocidad/baud rate)"),
    0xA2:  ("SV_CSUB",  "Direccion de subrutina a saltar al pulsar CAPSLOCK"),
    0xA6:  ("SV_TIMO",  "Timeout para el cambio de modo de transmision"),
    0xA8:  ("SV_TIMOV", "Valor del timeout de cambio (duracion de dos caracteres)"),
    0xAA:  ("SV_FSTAT", "Estado del cursor parpadeante"),
    0xEE:  ("SV_MDRUN", "Indica que unidad de Microdrive esta en marcha"),
    0xEF:  ("SV_MDCNT", "Contador de arranque/parada (run-up/run-down) de Microdrive"),
    0xF0:  ("SV_MDDID", "ID de unidad *4 de cada Microdrive (bloque de 8 bytes)"),
    0xF8:  ("SV_MDSTA", "Estado de cada Microdrive; 0 = sin operaciones pendientes (8 bytes)"),
    0x100: ("SV_FSDEF", "Punteros a los bloques de definicion fisica del sist. de ficheros (16 longs)"),
    0x140: ("SV_FSLST", "Puntero a la lista de definiciones de canal de fichero"),
}


# ---------------------------------------------------------------------------
# Utilidades de bajo nivel sobre la API de Ghidra
# ---------------------------------------------------------------------------

def get_scalar_operand(instr, opindex):
    """Devuelve el valor entero de un operando si es un escalar inmediato."""
    try:
        objs = instr.getOpObjects(opindex)
    except Exception:
        return None
    for o in objs:
        if isinstance(o, Scalar):
            return o.getUnsignedValue()
    return None


def get_register_operand(instr, opindex):
    """Devuelve el nombre de un registro si el operando lo contiene."""
    try:
        objs = instr.getOpObjects(opindex)
    except Exception:
        return None
    for o in objs:
        # Un operando indexado tipo "$34(A6)" trae [Scalar, Register]:
        # descartamos explicitamente los Scalar y nos quedamos con lo que
        # tenga getName() (los objetos Register de Ghidra la tienen).
        if isinstance(o, Scalar):
            continue
        if hasattr(o, "getName"):
            try:
                name = o.getName()
                if name:
                    return str(name)
            except Exception:
                pass
    return None


def get_dest_register(instr):
    """En sintaxis Motorola el destino suele ser el ultimo operando."""
    n = instr.getNumOperands()
    if n == 0:
        return None
    return get_register_operand(instr, n - 1)


def uses_register(instr, regname):
    """True si alguno de los operandos de instr referencia regname."""
    n = instr.getNumOperands()
    for i in range(n):
        r = get_register_operand(instr, i)
        if r is not None and r.upper() == regname.upper():
            return True
    return False


def get_disp_and_base(instr, opindex):
    """
    Si el operando opindex es una direccion indexada del tipo
    'desplazamiento(An)' (p.ej. "$34(A6)"), devuelve (desplazamiento_con_signo,
    nombre_de_registro). Si no encaja ese patron, devuelve None.
    """
    try:
        objs = instr.getOpObjects(opindex)
    except Exception:
        return None
    scalar = None
    reg = None
    for o in objs:
        if isinstance(o, Scalar):
            scalar = o
        elif hasattr(o, "getName"):
            try:
                nm = o.getName()
                if isinstance(nm, (str, unicode)):
                    reg = nm
            except Exception:
                pass
    if scalar is not None and reg is not None:
        return (scalar.getValue(), reg)
    return None


def find_d0_key(trap_instr, max_back=25):
    """
    Busca hacia atras, en linea recta, la ultima instruccion que carga un
    valor inmediato en D0 antes de la TRAP. Se detiene en el primer branch,
    llamada o retorno (heuristico simple para una primera pasada).
    Devuelve el valor entero, o None si no se pudo determinar.
    """
    instr = trap_instr.getPrevious()
    steps = 0
    while instr is not None and steps < max_back:
        mnem = instr.getMnemonicString().upper()

        if mnem.startswith("B") or mnem in ("JMP", "JSR", "RTS", "RTE", "RTR", "DBRA", "TRAP"):
            break

        if mnem.startswith("MOVE"):
            dest = get_dest_register(instr)
            if dest is not None and dest.upper() == "D0":
                val = get_scalar_operand(instr, 0)
                return val  # puede ser None si el origen no era inmediato

        instr = instr.getPrevious()
        steps += 1
    return None


def get_trap_number(trap_instr):
    val = get_scalar_operand(trap_instr, 0)
    return val


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def annotate_traps(listing):
    count_ok = 0
    count_unknown = 0
    trap_tables = {1: TRAP1, 2: TRAP2, 3: TRAP3}

    for instr in listing.getInstructions(True):
        mnem = instr.getMnemonicString().upper()
        if mnem != "TRAP":
            continue

        trapnum = get_trap_number(instr)
        if trapnum is None:
            continue

        addr = instr.getAddress()

        if trapnum == 0:
            comment = "QDOS TRAP #0: entra en modo supervisor (guardar SR antes de llamar)"
            count_ok += 1
        elif trapnum == 4:
            comment = ("QDOS TRAP #4: trap especial de SuperBASIC - hace que las "
                       "direcciones pasadas al siguiente trap (#2/#3) sean relativas a A6")
            count_ok += 1
        elif trapnum in trap_tables:
            key = find_d0_key(instr)
            table = trap_tables[trapnum]
            if key is not None and key in table:
                name, desc = table[key]
                comment = "QDOS TRAP #%d  D0=$%02X  %s: %s" % (trapnum, key, name, desc)
                count_ok += 1
            elif key is not None:
                comment = ("QDOS TRAP #%d  D0=$%02X  (clave no reconocida / fuera de tabla)"
                           % (trapnum, key))
                count_unknown += 1
            else:
                comment = ("QDOS TRAP #%d  (clave en D0 no determinada estaticamente; "
                           "revisar manualmente)" % trapnum)
                count_unknown += 1
        else:
            comment = "TRAP #%d (fuera del rango 0-4 usado por Qdos)" % trapnum
            count_unknown += 1

        instr.setComment(CodeUnit.EOL_COMMENT, comment)
        try:
            createBookmark(addr, "QDOS", comment)
        except Exception:
            pass

    return count_ok, count_unknown


def annotate_vectors(listing):
    count_ok = 0

    for instr in listing.getInstructions(True):
        mnem = instr.getMnemonicString().upper()
        if not mnem.startswith("MOVE"):
            continue
        if instr.getNumOperands() != 2:
            continue

        dest = get_dest_register(instr)
        if dest is None or not dest.upper().startswith("A"):
            continue

        val = get_scalar_operand(instr, 0)
        if val is None or val not in VECTORS:
            continue

        # Buscar hacia adelante el JSR/JMP que usa ese registro
        nxt = instr.getNext()
        steps = 0
        while nxt is not None and steps < 4:
            nmnem = nxt.getMnemonicString().upper()
            if nmnem in ("JSR", "JMP"):
                if uses_register(nxt, dest):
                    name, desc = VECTORS[val]
                    extra = ""
                    if val in VECTORS_OFFSET_4000:
                        extra = "  [normalmente invocada como JSR $4000(An)]"
                    comment = "QDOS vector $%X  %s: %s%s" % (val, name, desc, extra)
                    nxt.setComment(CodeUnit.EOL_COMMENT, comment)
                    try:
                        createBookmark(nxt.getAddress(), "QDOS", comment)
                    except Exception:
                        pass
                    count_ok += 1
                break
            if nmnem.startswith("B") or nmnem in ("RTS", "RTE", "RTR", "TRAP"):
                break
            nxt = nxt.getNext()
            steps += 1

    return count_ok


def run():
    program = currentProgram
    listing = program.getListing()

    println("QL_QdosTrapAnnotator: analizando TRAPs #0-#4 ...")
    trap_ok, trap_unknown = annotate_traps(listing)
    println("  -> %d traps anotados, %d con clave no determinada" % (trap_ok, trap_unknown))

    println("QL_QdosTrapAnnotator: analizando llamadas a rutinas vectorizadas ...")
    vec_ok = annotate_vectors(listing)
    println("  -> %d llamadas a vectores QDOS anotadas" % vec_ok)

    println("Hecho. Revisa los comentarios EOL y los bookmarks de categoria 'QDOS'.")


run()
