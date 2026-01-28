const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "login.html";
}

fetch("/api/auth/profile", {
    headers: {
        "Authorization": `Bearer ${token}`
    }
})
.then(res => {
    if (!res.ok) throw new Error("Unauthorized");
    return res.json();
})
.then(data => {
    document.getElementById("username").innerText = data.username;
    document.getElementById("email").innerText = data.email;
})
.catch(() => {
    alert("Failed to load profile");
});
