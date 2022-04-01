document.addEventListener('DOMContentLoaded', () => {
  // notification
  document.querySelectorAll('.notification').forEach(notification => {
    if (notification.querySelector('.delete')) {
      notification.querySelector('.delete').addEventListener('click', () => {
        notification.parentNode.removeChild(notification);
      });
    }
  });

  // project card
  document.querySelectorAll('.project-card').forEach(projectCard => {
    projectCard.querySelectorAll('.tag-suggestion').forEach(tagSuggestion => {
      tagSuggestion.addEventListener('click', e => {
        e.preventDefault();
        projectCard.querySelector('[name=major]').setAttribute('value', tagSuggestion.getAttribute('data-major'));
        projectCard.querySelector('[name=minor]').setAttribute('value', tagSuggestion.getAttribute('data-minor'));
        projectCard.querySelector('[name=patch]').setAttribute('value', tagSuggestion.getAttribute('data-patch'));
        projectCard.querySelector('[name=fix]').setAttribute('value', tagSuggestion.getAttribute('data-fix'));
      });
    })
  });

  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', e => {
      document.querySelector('.progress-modal').classList.add('is-active');
    });
  })
});
