import React from 'react';
import { Navigate } from 'react-router-dom';
import { loadSession } from '../utils/session';

export default function ProtectedRoute({ children, roles }) {
  const session = loadSession();
  if (!session) {
    return <Navigate to="/" replace />;
  }
  if (roles?.length && !roles.includes(session.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}
