function env = configurePython(pythonExecutable)
% Configure MATLAB to call the Power Grid Sun Python environment.
arguments
    pythonExecutable (1,1) string
end
env = pyenv(Version=pythonExecutable, ExecutionMode="OutOfProcess");
disp(env)
end
