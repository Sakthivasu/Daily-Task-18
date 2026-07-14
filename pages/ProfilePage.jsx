import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import axios from 'axios';


const ProfilePage = () => {
  const { user, updateUser } = useContext(AuthContext);
  
  // State for forms
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [image, setImage] = useState(null);
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  // 1. Update Profile Info
  const handleProfileUpdate = async (e) => {
  e.preventDefault();

  try {
    const res = await axios.put(
      "http://localhost:5000/api/me",
      {
        name,
        email,
      },
      {
        withCredentials: true,
      }
    );

    console.log(res.data);

    updateUser({
      name,
      email,
    });

    alert("Profile updated successfully!");
  } catch (err) {
    console.error(err.response);
    alert(err.response?.data?.message || "Failed to update profile");
  }
};

  // 2. Upload Avatar
const handleAvatarUpload = async (e) => {
  e.preventDefault();

  if (!image) {
    alert("Please select an image first");
    return;
  }

  const formData = new FormData();
  formData.append("image", image);

  setLoading(true);

  try {
    const res = await axios.put(
      "http://localhost:5000/api/me/avatar",
      formData,
      {
        withCredentials: true,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    updateUser({ avatar_url: res.data.avatar_url });
    alert("Avatar updated successfully!");
  } catch (err) {
    console.error(err);
    alert(err.response?.data?.message || "Avatar upload failed.");
  } finally {
    setLoading(false);
  }
};
  
  // 3. Change Password
  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) return alert("New passwords do not match!");
    
    setLoading(true);
    try {
      await axios.put('http://localhost:5000/api/me/password', {
        current_password: passwords.current,
        new_password: passwords.new,
        confirm_password: passwords.confirm
      }, { withCredentials: true });
      alert("Password changed successfully!");
      setPasswords({ current: '', new: '', confirm: '' }); // Clear fields
    } catch (err) {
      alert(err.response?.data?.message || "Error changing password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-container">
      <h2>My Profile Settings</h2>

      {/* Avatar Section */}
      <section className="profile-section">
        <img
  src={
    user?.avatar_url
      ? `http://localhost:5000${user.avatar_url}`
      : "/default-avatar.png"
  }
  alt="Avatar"
  onError={(e) => {
    e.target.src = "/default-avatar.png";
  }}
  className="avatar-preview"
  style={{
    width: "120px",
    height: "120px",
    borderRadius: "50%",
    objectFit: "cover",
    border: "3px solid #1e293b",
  }}
/>
        <form onSubmit={handleAvatarUpload} className="form-group">
          <input type="file" onChange={(e) => setImage(e.target.files[0])} />
          <button type="submit" disabled={loading}>
            {loading ? "Processing..." : "Update Photo"}
          </button>
        </form>
      </section>

      {/* Profile Form */}
      <form onSubmit={handleProfileUpdate} className="form-group">
        <label>Full Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
        <label>Email Address</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        <button type="submit" disabled={loading}>Save Profile Info</button>
      </form>

      {/* Password Form */}
      <form onSubmit={handlePasswordChange} className="form-group">
        <h3>Change Password</h3>
        <input type="password" placeholder="Current Password" 
               onChange={(e) => setPasswords({...passwords, current: e.target.value})} required />
        <input type="password" placeholder="New Password" 
               onChange={(e) => setPasswords({...passwords, new: e.target.value})} required />
        <input type="password" placeholder="Confirm New Password" 
               onChange={(e) => setPasswords({...passwords, confirm: e.target.value})} required />
        <button type="submit" className="btn-danger" disabled={loading}>Change Password</button>
      </form>
    </div>
  );
};

export default ProfilePage;