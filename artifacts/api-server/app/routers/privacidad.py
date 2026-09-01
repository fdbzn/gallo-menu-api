"""Página pública de Política de Privacidad para Moussi (requerida por Google Play Store)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

_HTML_CONTENT = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Política de Privacidad - Moussi</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {
      --primary: #9c27b0;
      --primary-dark: #7B1FA2;
      --primary-light: #f3e5f5;
      --bg: #faf7fb;
      --surface: #ffffff;
      --text: #1d1b20;
      --text-muted: #49454f;
      --border: #e7e0ec;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 24px 16px;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      background: var(--surface);
      border-radius: 24px;
      padding: 40px 32px;
      box-shadow: 0 4px 20px rgba(156, 39, 176, 0.06);
      border: 1px solid var(--border);
    }
    header {
      text-align: center;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
    }
    .logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      background: var(--primary);
      color: #fff;
      border-radius: 16px;
      font-weight: 700;
      font-size: 24px;
      margin-bottom: 12px;
    }
    h1 {
      font-size: 28px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
    }
    .updated {
      font-size: 14px;
      color: var(--text-muted);
    }
    h2 {
      font-size: 20px;
      font-weight: 600;
      color: var(--primary-dark);
      margin-top: 28px;
      margin-bottom: 12px;
    }
    p, ul {
      margin-bottom: 16px;
      color: var(--text-muted);
      font-size: 15px;
    }
    ul {
      padding-left: 24px;
    }
    li {
      margin-bottom: 8px;
    }
    .card {
      background: var(--primary-light);
      border-left: 4px solid var(--primary);
      padding: 16px;
      border-radius: 8px;
      margin: 20px 0;
      color: #4a148c;
      font-size: 14px;
    }
    footer {
      text-align: center;
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 13px;
      color: var(--text-muted);
    }
    a {
      color: var(--primary);
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo">M</div>
      <h1>Política de Privacidad</h1>
      <p class="updated">Última actualización: 31 de agosto de 2026</p>
    </header>

    <div class="card">
      Esta Política de Privacidad describe cómo <strong>Moussi</strong> ("nosotros", "la aplicación") recopila, utiliza y protege la información personal de los usuarios al utilizar nuestra aplicación móvil y servicios asociados.
    </div>

    <h2>1. Información que recopilamos</h2>
    <p>Para proporcionar y mejorar nuestros servicios de planificación colaborativa de menús y listas de compras, recopilamos la siguiente información:</p>
    <ul>
      <li><strong>Información de la cuenta:</strong> Correo electrónico, nombre completo o alias, y contraseña (encriptada de forma segura).</li>
      <li><strong>Datos de contenido del usuario:</strong> Menús planificados, platillos, recetas, ingredientes, listas de compras y mesas de trabajo colaborativas creadas dentro de la app.</li>
      <li><strong>Información de uso:</strong> Registros de interacción básica necesarios para sincronizar datos en tiempo real entre los miembros de una mesa compartida.</li>
    </ul>

    <h2>2. Uso de la información</h2>
    <p>Utilizamos la información recopilada exclusivamente para:</p>
    <ul>
      <li>Autenticar tu identidad y mantener tu sesión activa de forma segura.</li>
      <li>Permitir la colaboración en tiempo real con amigos, familiares o roomies en tus menús y listas de compras.</li>
      <li>Sincronizar tus datos entre tus dispositivos.</li>
      <li>Enviar correos transaccionales esenciales (confirmación de cuenta y restablecimiento de contraseña).</li>
    </ul>

    <h2>3. Almacenamiento y Protección de Datos</h2>
    <p>La seguridad de tus datos es nuestra máxima prioridad:</p>
    <ul>
      <li>Toda la comunicación entre la aplicación móvil y nuestros servidores se realiza mediante protocolos seguros y cifrados (HTTPS / SSL / TLS).</li>
      <li>Las contraseñas y credenciales de acceso se almacenan cifradas mediante estándares de la industria a través de nuestra infraestructura de autenticación (Supabase Auth).</li>
      <li>No vendemos, alquilamos ni comercializamos tu información personal a terceros bajo ninguna circunstancia.</li>
    </ul>

    <h2>4. Servicios de Terceros</h2>
    <p>Moussi utiliza servicios de terceros de alta confiabilidad para su infraestructura:</p>
    <ul>
      <li><strong>Supabase:</strong> Plataforma de autenticación y base de datos segura (PostgreSQL).</li>
      <li><strong>Expo / EAS:</strong> Plataforma para la entrega y actualización del software móvil.</li>
    </ul>

    <h2>5. Derechos del Usuario y Eliminación de Datos</h2>
    <p>Tienes pleno control sobre tu información:</p>
    <ul>
      <li><strong>Acceso y Modificación:</strong> Puedes ver y editar los datos de tu perfil en cualquier momento desde la sección de configuración de la app.</li>
      <li><strong>Eliminación de Cuenta y Datos:</strong> Si deseas eliminar permanentemente tu cuenta y todos los datos asociados (platillos, menús, listas de compras), puedes solicitarlo desde la aplicación o enviando un correo a soporte. Todos tus datos serán eliminados irrevocablemente de nuestros servidores.</li>
    </ul>

    <h2>6. Privacidad de Menores</h2>
    <p>Moussi no está dirigida a niños menores de 13 años. No recopilamos conscientemente información personal de menores de 13 años. Si descubrimos que un menor de 13 años nos ha proporcionado información personal, procederemos a eliminarla de inmediato.</p>

    <h2>7. Cambios a esta Política</h2>
    <p>Podemos actualizar nuestra Política de Privacidad periódicamente. Te notificaremos sobre cualquier cambio publicando la nueva Política de Privacidad en esta página con una fecha de actualización revisada.</p>

    <h2>8. Contacto</h2>
    <p>Si tienes preguntas, dudas o solicitudes relacionadas con esta Política de Privacidad o el tratamiento de tus datos, puedes contactarnos a través de:</p>
    <ul>
      <li><strong>Correo de soporte:</strong> <a href="mailto:soporte@moussi.app">soporte@moussi.app</a></li>
    </ul>

    <footer>
      &copy; 2026 Moussi. Todos los derechos reservados.
    </footer>
  </div>
</body>
</html>
"""


@router.get("/privacidad", response_class=HTMLResponse, include_in_schema=False)
@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
@router.get("/privacy-policy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_policy():
    """Retorna la página pública de política de privacidad requerida para Google Play Store."""
    return HTMLResponse(content=_HTML_CONTENT)
