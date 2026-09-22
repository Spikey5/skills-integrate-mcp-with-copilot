document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const authMessage = document.getElementById("auth-message");
  const authContainer = document.getElementById("auth-container");
  const appShell = document.getElementById("app-shell");
  const signupContainer = document.getElementById("signup-container");
  const roleNotice = document.getElementById("role-notice");
  const authToken = {
    value: localStorage.getItem("mergington-auth-token"),
  };
  let currentUser = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#039;",
      '"': "&quot;",
    }[character]));
  }

  async function request(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (authToken.value) {
      headers.Authorization = `Bearer ${authToken.value}`;
    }
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(url, { ...options, headers });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Something went wrong");
    }
    return result;
  }

  function showMessage(element, text, type) {
    element.textContent = text;
    element.className = type;
    element.classList.remove("hidden");
  }

  function showUnauthenticated() {
    authContainer.classList.remove("hidden");
    appShell.classList.add("hidden");
  }

  function showAuthenticated(user) {
    currentUser = user;
    authContainer.classList.add("hidden");
    appShell.classList.remove("hidden");
    document.getElementById("current-user").textContent = user.email;
    document.getElementById("current-role").textContent = user.role_label;

    const canJoinActivities = user.role === "student";
    signupContainer.classList.toggle("hidden", !canJoinActivities);
    roleNotice.textContent = canJoinActivities
      ? "You can join activities and manage your own signups."
      : `${user.role_label} access is ready for role-specific tools.`;
    roleNotice.classList.remove("hidden");
    fetchActivities();
  }

  async function fetchActivities() {
    try {
      const activities = await request("/activities");
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft = details.max_participants - details.participants.length;
        const participantsHTML = details.participants.length > 0
          ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants.map((email) => `
                  <li>
                    <span class="participant-email">${escapeHtml(email)}</span>
                    ${currentUser && currentUser.email === email
                      ? `<button class="delete-btn" data-activity="${escapeHtml(name)}" type="button" aria-label="Unregister from ${escapeHtml(name)}">Remove</button>`
                      : ""}
                  </li>`).join("")}
              </ul>
            </div>`
          : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>`;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    try {
      const activity = event.currentTarget.dataset.activity;
      const result = await request(`/activities/${encodeURIComponent(activity)}/unregister`, {
        method: "DELETE",
      });
      showMessage(messageDiv, result.message, "success");
      fetchActivities();
    } catch (error) {
      showMessage(messageDiv, error.message, "error");
    }
  }

  document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const isLogin = tab.dataset.authMode === "login";
      document.querySelectorAll(".auth-tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById("login-form").classList.toggle("hidden", !isLogin);
      document.getElementById("register-form").classList.toggle("hidden", isLogin);
      document.getElementById("auth-intro").textContent = isLogin
        ? "Sign in to join campus activities."
        : "Create an account with the role that matches your campus work.";
      authMessage.classList.add("hidden");
    });
  });

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        }),
      });
      authToken.value = result.token;
      localStorage.setItem("mergington-auth-token", result.token);
      showAuthenticated(result.user);
    } catch (error) {
      showMessage(authMessage, error.message, "error");
    }
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await request("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: document.getElementById("register-email").value,
          password: document.getElementById("register-password").value,
          role: document.getElementById("register-role").value,
        }),
      });
      authToken.value = result.token;
      localStorage.setItem("mergington-auth-token", result.token);
      showAuthenticated(result.user);
    } catch (error) {
      showMessage(authMessage, error.message, "error");
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await request("/auth/logout", { method: "POST" });
    } finally {
      authToken.value = null;
      localStorage.removeItem("mergington-auth-token");
      currentUser = null;
      showUnauthenticated();
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const activity = activitySelect.value;
      const result = await request(`/activities/${encodeURIComponent(activity)}/signup`, {
        method: "POST",
      });
      showMessage(messageDiv, result.message, "success");
      signupForm.reset();
      fetchActivities();
    } catch (error) {
      showMessage(messageDiv, error.message, "error");
    }
  });

  async function initialize() {
    if (!authToken.value) {
      showUnauthenticated();
      return;
    }
    try {
      showAuthenticated(await request("/auth/me"));
    } catch (error) {
      authToken.value = null;
      localStorage.removeItem("mergington-auth-token");
      showUnauthenticated();
    }
  }

  initialize();
});
