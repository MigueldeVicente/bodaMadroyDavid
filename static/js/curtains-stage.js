window.addEventListener('load', () => {
  const stage = document.querySelector('.curtain-stage');
  if (!stage) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { stage.remove(); return; }
  setTimeout(() => stage.classList.add('curtain-stage--open'), 700);
  setTimeout(() => stage.remove(), 3600);
});
