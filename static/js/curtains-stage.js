document.addEventListener('DOMContentLoaded', () => {
  const stage = document.getElementById('curtain-stage');

  if (!stage) {
    document.body.classList.remove('curtain-active');
    return;
  }

  const finish = () => {
    if (stage.classList.contains('is-finished')) return;

    stage.classList.add('is-finished');
    document.body.classList.remove('curtain-active');
    window.setTimeout(() => stage.remove(), 400);
  };

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    stage.remove();
    document.body.classList.remove('curtain-active');
    return;
  }

  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => stage.classList.add('is-opening'));
  });

  const rightCurtain = stage.querySelector('.curtain-right');
  rightCurtain.addEventListener('transitionend', (event) => {
    if (event.propertyName === 'transform') finish();
  }, { once: true });

  window.setTimeout(finish, 3400);
});
