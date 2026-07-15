document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registro-form');
  const alert = document.getElementById('form-alert');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.textContent = 'Buscando tus misiones…';
    alert.textContent = '';

    try {
      const response = await fetch('/api/invitado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(new FormData(form)))
      });

      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error || 'No se pudo completar el registro.');
      }

      window.location.assign(result.redirect || '/misiones');
    } catch (error) {
      alert.textContent = error.message;
      button.disabled = false;
      button.innerHTML = originalText;
    }
  });
});
