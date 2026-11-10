# 🚀 Instrucciones para Actualizar tu App de Streamlit Cloud

## 📍 Tu Repositorio Actual

- **GitHub**: https://github.com/IA-P1-BCN/EDA-Anna_Costa.git
- **Rama**: `main` ✅ (con última versión)
- **URL Streamlit**: https://eda-costanna.streamlit.app/

---

## 🔄 PASO A PASO para Actualizar la App

### **Paso 1: Verificar que los cambios están en GitHub**

```bash
# En tu terminal local:
cd D:/-GEEK-/FACTORIA F5/IA/PROYECTOS/M2/ai_project_EDA
git status
# Debería decir "nothing to commit, working tree clean"

git log -1
# Verás: fc61ac2 Actualizar README con instrucciones...
```

### **Paso 2: Ir a Streamlit Cloud**

1. Abre https://streamlit.io/cloud/new
2. Haz clic en **"Sign in with GitHub"**
3. Selecciona tu cuenta de GitHub

### **Paso 3: Conectar el Repositorio**

Streamlit te mostrará los repositorios que tienes. Deberías ver:

```
EDA-Anna_Costa (IA-P1-BCN)
```

- Click en **"Connect"**
- Streamlit escaneará el repositorio automáticamente

### **Paso 4: Configurar la App**

Streamlit detectará `app.py` y te mostrará:

```
Detected app: /app/app.py
Branch: main
```

Click en **"Deploy"** o **"Deploy app"**

### **Paso 5: Configurar URL Personalizada (opcional)**

Después del despliegue, ve a **Settings → App settings**:

1. En **"App name"**, cambia a: `eda-costanna`
2. Streamlit generará automáticamente: `https://eda-costanna.streamlit.app/`
3. Click en **"Save"**

### **Paso 6: Reiniciar el Deploy** ⚠️ IMPORTANTE

Para que cargue la nueva versión inmediatamente:

1. Click en **"Manage app"** (abajo a la derecha)
2. Scroll al fondo → **"Restart"**
3. Espera ~2 minutos mientras se reinicia

### **Paso 7: Verificar el Deploy**

La app debería cargar con estas características:

✅ Mensaje de carga: `✅ Cargados 628,262 registros de 50 estados`  
✅ Selector de métrica con opciones:
   - `casos_acum`
   - `muertes_acum`
   - `hospitalizados_actuales`
   - `tests_acum`
   - etc.

✅ Filtros temporales: "Completo", "-30 días", "-60 días", "-90 días"  
✅ Tabla interactiva por estado  
✅ Botón "Descargar CSV"  

---

## 🎯 ¿Qué Esperar al Abrir la App?

### **Pantalla de Inicio:**

```
📦 Información de carga
✅ Cargados 628,262 registros de 50 estados
📅 Rango de datos: 03/02/2020 - 12/31/2021

4 Tarjetas:
┌─────────┬─────────┬─────────┬─────────┐
│ Casos Acum │ Letalidad │ Hospitalizados │ Población │
│ XXX,XXX │ X.XX%   │ XXXXX   │ Por Habitante │
└─────────┴─────────┴─────────┴─────────┘
```

### **Sidebar:**

- Selector de métrica: `casos_acum` (por defecto)
- Filtro temporal: "Completo" (por defecto)
- Mostrará rango de fecha actualizado

### **Páginas del Dashboard:**

1. **📊 Resumen del Período** - 4 tarjetas con métricas clave
2. **🗺️ Datos por Estado** - Tabla Top 30 ordenada
3. **🔍 Comparación de Métricas** - Vista multi-métrica
4. **📅 Filtros Activos** - Información del rango temporal

---

## 🔧 Si la App no Actualiza Automáticamente

### **Opción A: Reiniciar desde Streamlit Cloud**

1. Ve a tu app: https://eda-costanna.streamlit.app/
2. Click en **"Manage app"** (abajo a la derecha)
3. Scroll al fondo → botón **"Restart"**
4. Espera 2-3 minutos
5. Recarga con F5

### **Opción B: Reiniciar desde GitHub**

1. Ve a https://github.com/IA-P1-BCN/EDA-Anna_Costa/settings/deployments
2. Verás el deployment de Streamlit Cloud
3. Click en los 3 puntos (⋮) → **"Actions"** o **"Restart"**
4. Espera ~3 minutos

### **Opción C: Limpiar Caché del Navegador**

1. Abre ventana nueva del navegador
2. Ve a https://eda-costanna.streamlit.app/
3. O presiona: `Ctrl + Shift + R` (en Windows/Linux) o `Cmd + Shift + R` (Mac)

---

## 📊 Verificar que Funciona Correctamente

### **Test Básico:**

1. **Selector de métrica** debe mostrar opciones:
   - ✅ `casos_acum`
   - ✅ `muertes_acum`
   - ✅ `hospitalizados_actuales`
   - ✅ `tests_acum`

2. **Cambiar filtro temporal**:
   - Click en "-30 días" → Debe mostrar rango de fechas del dataset (ej: Oct 2021)
   - No debe mostrar "nan" o valores faltantes

3. **Tabla por estado** debe mostrar Top 30 con valores numéricos

### **Si ves "nan" en las métricas:**

Esto significa que los datos están acumulativos y pocos estados tienen registros individuales. Usa el filtro **"Completo"** para ver todos los datos disponibles.

---

## 📝 Comandos Útiles para GitHub

### **Verificar estado del repo:**

```bash
# Ver ramas y commits actuales
git branch -v
git log --oneline -5

# Ver que app.py está en main
git show HEAD:app.py | head -20

# Push cambios a main
git push origin main
```

### **Crear backup antes de actualizar:**

```bash
# Crear rama de backup
git checkout -b backup-streamlit

# Si necesitas revertir cambios:
git reset --hard HEAD~1
git push origin main --force
```

---

## 🆘 Solución de Problemas Comunes

### **Error: "Cannot find app.py"**

**Causa**: El archivo `app.py` no existe o está mal nombrado.

**Solución**:
1. Verifica que `app.py` existe en el repo
2. GitHub → EDA-Anna_Costa → Files → Deberías ver `app.py` arriba

### **Error: "Data loading failed"**

**Causa**: Los archivos CSV no están en la ruta correcta.

**Solución**:
1. Verifica que existen en Git: `git ls-files data/processed/*.csv`
2. Descarga de los archivos CSV se hace desde el repo local, no desde GitHub Raw

### **Error: "StreamlitValueError: divider='primary'"**

**Causa**: Parámetro deprecated en Streamlit 1.27+.

**Solución**: Ya corregido - la versión actual usa `divider="blue"` (valor nativo de Streamlit)

---

## ✅ Checklist Final

Antes de desplegar, verifica:

- [ ] `app.py` está en Git y es la versión sin Plotly
- [ ] Datos CSV están en `data/processed/`
- [ ] `.streamlit/config.toml` existe con configuración
- [ ] `requirements.txt` incluye pandas y streamlit
- [ ] README.md tiene instrucciones de despliegue

---

## 📞 Ayuda Adicional

Si encuentras algún problema durante el despliegue:

1. **Captura una captura de pantalla del error**
2. **Copia el mensaje de error completo**
3. **Dímelo y ajustaremos el código específico**

---

**¡Listo para desplegar!** 🚀

Los cambios ya están en GitHub y listos para deploy automático. Solo sigue los pasos 1-6 de arriba para actualizar tu app en https://eda-costanna.streamlit.app/