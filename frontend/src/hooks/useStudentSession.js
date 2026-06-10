import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession } from '../utils/session';

export function useStudentSession() {
  const navigate = useNavigate();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const session = loadSession();
    if (!session || session.role !== 'student' || !session.student_id) {
      navigate('/');
      return;
    }
    setIsReady(true);
  }, [navigate]);

  return isReady;
}
