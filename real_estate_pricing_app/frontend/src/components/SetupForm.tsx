import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SetupForm: React.FC = () => {
  const [stage, setStage] = useState('initial');
  const [goal, setGoal] = useState('quick');
  const [sellerType, setSellerType] = useState('fsbo');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('sellerProfile', JSON.stringify({ stage, goal, sellerType }));
    navigate('/chat');
  };

  return (
    <div className="setup-container">
      <h2>Setup Your Profile</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Listing Stage:</label>
          <select value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="initial">Setting Initial Price</option>
            <option value="active">Active Listing</option>
          </select>
        </div>
        <div>
          <label>Goal:</label>
          <select value={goal} onChange={(e) => setGoal(e.target.value)}>
            <option value="quick">Quick Sale</option>
            <option value="maximum">Maximum Price</option>
          </select>
        </div>
        <div>
          <label>Seller Type:</label>
          <select value={sellerType} onChange={(e) => setSellerType(e.target.value)}>
            <option value="fsbo">For Sale By Owner (FSBO)</option>
            <option value="agent">Working with Agent</option>
          </select>
        </div>
        <button type="submit">Continue to Chat</button>
      </form>
    </div>
  );
};

export default SetupForm;
