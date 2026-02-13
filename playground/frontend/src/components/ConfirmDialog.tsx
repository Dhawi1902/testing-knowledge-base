interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="modal-overlay" data-testid="confirm-dialog">
      <div className="modal">
        <h3>{title}</h3>
        <p style={{ margin: '1rem 0', color: '#555' }}>{message}</p>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn-secondary" data-testid="confirm-cancel">
            Cancel
          </button>
          <button onClick={onConfirm} className="btn-danger" data-testid="confirm-ok">
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
