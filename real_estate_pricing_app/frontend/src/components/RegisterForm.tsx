import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const RegisterForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [needsConfirmation, setNeedsConfirmation] = useState(false);
  const [error, setError] = useState('');
  const { register, confirmRegistration } = useAuth();
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      await register(email, password);
      setNeedsConfirmation(true);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await confirmRegistration(email, code);
      navigate('/login');
    } catch (err: any) {
      setError(err.message || 'Confirmation failed');
    }
  };

  if (needsConfirmation) {
    return (
      <div className="auth-container">
        <h1 className="app-title">Real Estate Pricing Advisor</h1>
        <h2>Confirm Registration</h2>
        <form onSubmit={handleConfirm}>
          <input
            type="text"
            placeholder="Confirmation Code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          {error && <div className="error">{error}</div>}
          <button type="submit">Confirm</button>
        </form>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <h1 className="app-title">Real Estate Pricing Advisor</h1>
      <h2>Register</h2>
      <form onSubmit={handleRegister}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />
        {error && <div className="error">{error}</div>}
        <button type="submit">Register</button>
      </form>
      <p>
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
};

export default RegisterForm;
