import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession } from '../utils/session';

export function useAdminSession() {
  const navigate = useNavigate();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const session = loadSession();
    if (!session || session.role !== 'admin') {
      navigate('/');
      return;
    }
    setIsReady(true);
  }, [navigate]);

  return isReady;
}
