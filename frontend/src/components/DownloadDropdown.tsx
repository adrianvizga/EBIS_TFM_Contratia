import { useState, useRef, useEffect } from 'react';
import { FaDownload, FaFilePdf, FaFileWord, FaSpinner } from 'react-icons/fa';

interface DownloadDropdownProps {
    onDownloadPDF: () => void;
    onDownloadDOCX: () => void;
    disabled?: boolean;
    loading?: boolean;
    variant?: 'icon' | 'button';
    buttonClassName?: string;
    label?: string;
}

export default function DownloadDropdown({
    onDownloadPDF,
    onDownloadDOCX,
    disabled = false,
    loading = false,
    variant = 'icon',
    buttonClassName,
    label,
}: DownloadDropdownProps) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const handleOption = (fn: () => void) => {
        setOpen(false);
        fn();
    };

    const isDisabled = disabled || loading;

    const triggerButton =
        variant === 'icon' ? (
            <button
                onClick={() => !isDisabled && setOpen(o => !o)}
                disabled={isDisabled}
                className={buttonClassName ?? 'p-2 rounded-lg transition-colors text-dark-600 dark:text-dark-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer'}
            >
                {loading ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaDownload className="w-4 h-4" />}
            </button>
        ) : (
            <button
                onClick={() => !isDisabled && setOpen(o => !o)}
                disabled={isDisabled}
                className={buttonClassName ?? 'inline-flex items-center gap-2 px-6 py-3 bg-primary-100 dark:bg-primary-900/30 hover:bg-primary-200 dark:hover:bg-primary-900/50 disabled:opacity-50 disabled:cursor-not-allowed text-primary-700 dark:text-primary-300 font-medium rounded-lg transition-colors text-sm border border-primary-200 dark:border-primary-800'}
            >
                {loading ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaDownload className="w-4 h-4" />}
                {label && <span>{label}</span>}
            </button>
        );

    return (
        <div ref={ref} className="relative">
            {triggerButton}
            {open && (
                <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-dark-800 border border-dark-200 dark:border-dark-700 rounded-lg shadow-lg z-50 overflow-hidden">
                    <button
                        onClick={() => handleOption(onDownloadPDF)}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors"
                    >
                        <FaFilePdf className="w-4 h-4 text-red-500 flex-shrink-0" />
                        PDF
                    </button>
                    <button
                        onClick={() => handleOption(onDownloadDOCX)}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors"
                    >
                        <FaFileWord className="w-4 h-4 text-blue-600 flex-shrink-0" />
                        Word (.docx)
                    </button>
                </div>
            )}
        </div>
    );
}
