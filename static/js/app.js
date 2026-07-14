document.addEventListener('DOMContentLoaded', () => {
  const registroForm = document.getElementById('registro-form');
  if (registroForm) registroForm.addEventListener('submit', handleRegistro);
  document.querySelectorAll('[data-upload-form]').forEach(setupUpload);
  updateProgress();
});

async function handleRegistro(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const alert = document.getElementById('form-alert');
  const button = form.querySelector('button[type="submit"]');
  const label = button.textContent;
  alert.className = 'alert';
  alert.textContent = '';
  button.disabled = true;
  button.textContent = 'Preparando tus misiones…';
  try {
    const response = await fetch('/api/registro', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo registrar.');
    window.location.assign('/misiones');
  } catch (error) {
    alert.className = 'alert error';
    alert.textContent = error.message;
    button.disabled = false;
    button.textContent = label;
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
  status.className = 'mission-status loading';
  status.textContent = 'Subiendo tu recuerdo…';
  try {
    const response = await fetch(form.action, { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo subir la foto.');
    preview.src = `${data.photo_url}${data.photo_url.includes('?') ? '&' : '?'}t=${Date.now()}`;
    preview.hidden = false;
    form.hidden = true;
    status.className = 'mission-status done';
    status.textContent = '¡Misión completada! Gracias por compartir.';
    updateProgress();
  } catch (error) { status.className = 'mission-status'; status.textContent = error.message; }
}

function updateProgress() {
  const pill = document.getElementById('progress-pill');
  if (pill) pill.textContent = `${document.querySelectorAll('.mission-status.done').length} de ${document.querySelectorAll('.mission-card').length} misiones completadas`;
}
