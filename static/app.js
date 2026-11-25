document.querySelectorAll("[data-suggest]").forEach(button => {
  button.addEventListener("click", () => {
    const input = document.getElementById("chat-input");
    if (input) { input.value = button.dataset.suggest; input.focus(); }
  });
});
