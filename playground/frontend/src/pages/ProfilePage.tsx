import { useState, useEffect, useRef } from 'react';
import { useToast } from '../components/Toast';
import Navbar from '../components/Navbar';
import { getUserProfile, updateProfile, uploadAvatar, getCsrfTokens } from '../services/api';

export default function ProfilePage() {
  const { addToast } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getUserProfile()
      .then((data) => {
        setProfile(data);
        setDisplayName(data.display_name);
      })
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const csrf = await getCsrfTokens();
      await updateProfile({ displayName, _csrf: csrf._csrf, _formId: csrf._formId });
      // Update localStorage user object
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      user.displayName = displayName;
      localStorage.setItem('user', JSON.stringify(user));
      addToast('Profile updated');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setSaving(false);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    // Preview
    const reader = new FileReader();
    reader.onload = () => setAvatarPreview(reader.result as string);
    reader.readAsDataURL(file);
  }

  async function handleAvatarUpload() {
    if (!avatarFile) return;
    setUploading(true);
    try {
      const csrf = await getCsrfTokens();
      const result = await uploadAvatar(avatarFile, csrf._csrf, csrf._formId);
      setProfile({ ...profile, avatar_url: result.avatarUrl });
      setAvatarFile(null);
      setAvatarPreview(null);
      addToast('Avatar uploaded');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <><Navbar /><main className="page-container"><p>Loading profile...</p></main></>
    );
  }

  return (
    <>
      <Navbar />
      <main className="page-container">
        <h1>Profile</h1>

        {error && <div className="error-message">{error}</div>}

        {profile && (
          <div className="profile-grid">
            {/* Avatar section */}
            <section className="detail-card profile-avatar-section">
              <div className="avatar-container">
                <div className="avatar-edit-wrapper" onClick={() => fileInputRef.current?.click()}>
                  {avatarPreview ? (
                    <img src={avatarPreview} alt="Preview" className="avatar-img" />
                  ) : profile.avatar_url ? (
                    <img src={`/api/users/${profile.avatar_url}`} alt="Avatar" className="avatar-img" />
                  ) : (
                    <div className="avatar-placeholder">
                      {profile.display_name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="avatar-overlay">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M16.5 3.5a2.121 2.121 0 113 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                    <span>Edit</span>
                  </div>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={handleFileSelect}
                  data-testid="avatar-input"
                  style={{ display: 'none' }}
                />
              </div>
              <h3 className="avatar-name">{profile.display_name}</h3>
              <span className="avatar-role">{profile.role}</span>
              <p className="avatar-hint">Click avatar to change photo</p>
              {avatarFile && (
                <button onClick={handleAvatarUpload} disabled={uploading} className="btn-primary" style={{ width: 'auto', marginTop: '0.75rem' }}>
                  {uploading ? 'Uploading...' : 'Upload Avatar'}
                </button>
              )}
            </section>

            {/* Profile info */}
            <section className="detail-card">
              <h2>Account Info</h2>
              <form onSubmit={handleSave}>
                <div className="form-group">
                  <label htmlFor="displayName">Display Name</label>
                  <input
                    id="displayName"
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={profile.email} disabled />
                </div>

                <div className="form-group">
                  <label>Role</label>
                  <input type="text" value={profile.role} disabled />
                </div>

                <div className="form-group">
                  <label>Verified</label>
                  <input type="text" value={profile.is_verified ? 'Yes' : 'No'} disabled />
                </div>

                <div className="form-group">
                  <label>Member Since</label>
                  <input type="text" value={new Date(profile.created_at).toLocaleDateString()} disabled />
                </div>

                <button type="submit" className="btn-primary" disabled={saving || displayName === profile.display_name}>
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </form>
            </section>
          </div>
        )}
      </main>
    </>
  );
}
