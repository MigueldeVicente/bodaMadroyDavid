document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registro-form');
  if (!form) return;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    localStorage.setItem(
      'boda-madro-david-invitado',
      JSON.stringify(Object.fromEntries(new FormData(form)))
    );
    window.location.assign('misiones.html');
  });
});
