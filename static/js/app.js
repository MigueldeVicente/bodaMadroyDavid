document.addEventListener('DOMContentLoaded', () => {
  runCurtainIntro();
  const registroForm = document.getElementById('registro-form');
  if (registroForm) registroForm.addEventListener('submit', handleRegistro);
  document.querySelectorAll('[data-upload-form]').forEach(setupUpload);
  updateProgress();
});

function runCurtainIntro() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const curtain = document.createElement('div');
  curtain.className = 'curtain';
  curtain.setAttribute('aria-hidden', 'true');
  curtain.innerHTML = '<div class="curtain__panel curtain__panel--left"><div class="curtain__fabric"></div></div><div class="curtain__panel curtain__panel--right"><div class="curtain__fabric"></div></div>';
  document.body.appendChild(curtain);
  window.setTimeout(() => curtain.classList.add('curtain--open'), 180);
  curtain.addEventListener('animationend', (event) => {
    if (event.target.classList.contains('curtain__panel')) curtain.remove();
  }, { once: true });
}

async function handleRegistro(event) {
  event.preventDefault();
  const form = event.target;
  const alert = document.getElementById('form-alert');
  const submitBtn = form.querySelector('button[type="submit"]');
  const defaultLabel = submitBtn.textContent;
  alert.className = 'alert'; alert.textContent = '';
  submitBtn.disabled = true; submitBtn.textContent = 'Preparando tus misiones…';
  const payload = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch('/api/registro', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error('Abre la boda con F5 (Flask), no con Live Server, para guardar invitados y misiones.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo registrar.');
    window.location.assign('/misiones');
  } catch (error) {
    alert.className = 'alert error'; alert.textContent = error.message;
    submitBtn.disabled = false; submitBtn.textContent = defaultLabel;
  }
}

function setupUpload(form) {
  const input = form.querySelector('input[type="file"]');
  input.addEventListener('change', () => { if (input.files?.length) uploadFile(form, input); });
}

async function uploadFile(form, input) {
  const file = input.files[0];
  const card = form.closest('.mission-card');
  const status = card.querySelector('.mission-status');
  const preview = card.querySelector('.mission-preview');
  if (!file?.type.startsWith('image/')) { status.textContent = 'Selecciona una imagen válida.'; return; }
  if (file.size > 16 * 1024 * 1024) { status.textContent = 'La foto no puede superar 16 MB.'; return; }
  status.className = 'mission-status loading'; status.textContent = 'Subiendo tu recuerdo…';
  try {
    const response = await fetch(form.action, { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo subir la foto.');
    preview.src = `${data.photo_url}${data.photo_url.includes('?') ? '&' : '?'}t=${Date.now()}`;
    preview.hidden = false; form.hidden = true;
    status.className = 'mission-status done'; status.textContent = '¡Misión completada! Gracias por compartir.';
    updateProgress();
  } catch (error) { status.className = 'mission-status'; status.textContent = error.message; }
}

function updateProgress() {
  const cards = document.querySelectorAll('.mission-card');
  const pill = document.getElementById('progress-pill');
  if (pill) pill.textContent = `${document.querySelectorAll('.mission-status.done').length} de ${cards.length} misiones completadas`;
}
